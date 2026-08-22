"""Recebimento e ciclo de vida de pedidos iFood para homologacao."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import get_session
from app.ifood_order_models import IfoodOrder
from app.integrations.ifood import (
    IfoodClientError,
    mark_order_action,
    order_detail,
    order_summary,
    process_order_events,
)
from app.routes.ifood_integration_routes import (
    _client,
    _credentials_configured,
    _get_config,
    _provider_http_status,
    _require_admin,
)

router = APIRouter(prefix="/integracoes/ifood", tags=["iFood pedidos"])


class IfoodCancellationPayload(BaseModel):
    reason: str = Field(min_length=1, max_length=64)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()


class IfoodCodePayload(BaseModel):
    code: str = Field(min_length=1, max_length=32)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip()


def _require_order_operations() -> None:
    if not bool(settings.IFOOD_ORDER_OPERATIONS_ENABLED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Operacoes de pedidos permanecem bloqueadas ate iniciar a "
                "homologacao controlada do iFood."
            ),
        )


def _order(db: Session, tenant_id, order_id: str) -> IfoodOrder:
    value = (
        db.query(IfoodOrder)
        .filter(
            IfoodOrder.tenant_id == tenant_id,
            IfoodOrder.ifood_order_id == order_id,
        )
        .first()
    )
    if value is None:
        raise HTTPException(status_code=404, detail="Pedido iFood nao encontrado.")
    return value


def _provider_failure(db: Session, config, exc: IfoodClientError) -> HTTPException:
    if config is not None:
        config.last_orders_error = str(exc)
        db.commit()
    return HTTPException(status_code=_provider_http_status(exc), detail=str(exc))


def _ensure_ready(db: Session, tenant_id):
    config = _get_config(db, tenant_id)
    if not config or not config.active or not config.merchant_id:
        raise HTTPException(
            status_code=409,
            detail="Ative a integracao e informe o Merchant ID antes de operar pedidos.",
        )
    if not _credentials_configured():
        raise HTTPException(
            status_code=503,
            detail="Credenciais do aplicativo iFood nao configuradas no servidor.",
        )
    return config


@router.get("/pedidos")
def list_ifood_orders(
    order_status: str | None = Query(default=None, alias="status", max_length=64),
    limit: int = Query(default=30, ge=1, le=100),
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = auth
    query = db.query(IfoodOrder).filter(IfoodOrder.tenant_id == tenant_id)
    if order_status:
        query = query.filter(IfoodOrder.status == order_status.strip().upper())
    orders = (
        query.order_by(IfoodOrder.last_event_at.desc(), IfoodOrder.id.desc())
        .limit(limit)
        .all()
    )
    return {"orders": [order_summary(order) for order in orders]}


@router.get("/pedidos/{order_id}")
def get_ifood_order(
    order_id: str,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _user, tenant_id = auth
    return order_detail(_order(db, tenant_id, order_id))


@router.post("/pedidos/processar-eventos")
def poll_ifood_order_events(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    _require_order_operations()
    config = _ensure_ready(db, tenant_id)
    try:
        with _client() as client:
            return process_order_events(
                db,
                tenant_id=tenant_id,
                config=config,
                client=client,
            )
    except IfoodClientError as exc:
        raise _provider_failure(db, config, exc) from exc


@router.get("/pedidos/{order_id}/motivos-cancelamento")
def get_ifood_cancellation_reasons(
    order_id: str,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    config = _ensure_ready(db, tenant_id)
    _order(db, tenant_id, order_id)
    try:
        with _client() as client:
            return {"reasons": client.cancellation_reasons(order_id)}
    except IfoodClientError as exc:
        raise _provider_failure(db, config, exc) from exc


def _run_simple_action(
    *,
    db: Session,
    config,
    order: IfoodOrder,
    action: Literal["confirm", "start_preparation", "ready_to_pickup", "dispatch"],
) -> dict[str, Any]:
    methods = {
        "confirm": "confirm_order",
        "start_preparation": "start_order_preparation",
        "ready_to_pickup": "mark_order_ready",
        "dispatch": "dispatch_order",
    }
    if action == "dispatch" and (
        order.order_type != "DELIVERY" or order.delivered_by != "MERCHANT"
    ):
        raise HTTPException(
            status_code=409,
            detail="Despacho manual so se aplica a DELIVERY com entrega da loja.",
        )
    try:
        with _client() as client:
            result = getattr(client, methods[action])(order.ifood_order_id)
        mark_order_action(order, action)
        db.commit()
        return {"accepted": True, "action": action, "provider": result}
    except IfoodClientError as exc:
        raise _provider_failure(db, config, exc) from exc


@router.post("/pedidos/{order_id}/confirmar")
def confirm_ifood_order(
    order_id: str,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    _require_order_operations()
    config = _ensure_ready(db, tenant_id)
    return _run_simple_action(
        db=db,
        config=config,
        order=_order(db, tenant_id, order_id),
        action="confirm",
    )


@router.post("/pedidos/{order_id}/iniciar-preparacao")
def start_ifood_order_preparation(
    order_id: str,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    _require_order_operations()
    config = _ensure_ready(db, tenant_id)
    return _run_simple_action(
        db=db,
        config=config,
        order=_order(db, tenant_id, order_id),
        action="start_preparation",
    )


@router.post("/pedidos/{order_id}/pronto")
def mark_ifood_order_ready(
    order_id: str,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    _require_order_operations()
    config = _ensure_ready(db, tenant_id)
    return _run_simple_action(
        db=db,
        config=config,
        order=_order(db, tenant_id, order_id),
        action="ready_to_pickup",
    )


@router.post("/pedidos/{order_id}/despachar")
def dispatch_ifood_order(
    order_id: str,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    _require_order_operations()
    config = _ensure_ready(db, tenant_id)
    return _run_simple_action(
        db=db,
        config=config,
        order=_order(db, tenant_id, order_id),
        action="dispatch",
    )


@router.post("/pedidos/{order_id}/cancelar")
def cancel_ifood_order(
    order_id: str,
    body: IfoodCancellationPayload,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    _require_order_operations()
    config = _ensure_ready(db, tenant_id)
    order = _order(db, tenant_id, order_id)
    try:
        with _client() as client:
            reasons = client.cancellation_reasons(order_id)
            allowed = {
                str(item.get("code") or item.get("reason") or "").strip()
                for item in reasons
            }
            if body.reason not in allowed:
                raise HTTPException(
                    status_code=422,
                    detail="Selecione um motivo de cancelamento retornado pelo iFood.",
                )
            result = client.request_order_cancellation(order_id, body.reason)
        mark_order_action(order, "request_cancellation")
        db.commit()
        return {"accepted": True, "action": "request_cancellation", "provider": result}
    except IfoodClientError as exc:
        raise _provider_failure(db, config, exc) from exc


def _validate_code(
    *,
    db: Session,
    config,
    order: IfoodOrder,
    code: str,
    action: Literal["validate_pickup_code", "verify_delivery_code"],
) -> dict[str, Any]:
    try:
        with _client() as client:
            result = getattr(client, action)(order.ifood_order_id, code)
        mark_order_action(order, action)
        db.commit()
        return result
    except IfoodClientError as exc:
        raise _provider_failure(db, config, exc) from exc


@router.post("/pedidos/{order_id}/validar-coleta")
def validate_ifood_pickup_code(
    order_id: str,
    body: IfoodCodePayload,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    _require_order_operations()
    config = _ensure_ready(db, tenant_id)
    return _validate_code(
        db=db,
        config=config,
        order=_order(db, tenant_id, order_id),
        code=body.code,
        action="validate_pickup_code",
    )


@router.post("/pedidos/{order_id}/validar-entrega")
def verify_ifood_delivery_code(
    order_id: str,
    body: IfoodCodePayload,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = auth
    _require_admin(current_user)
    _require_order_operations()
    config = _ensure_ready(db, tenant_id)
    return _validate_code(
        db=db,
        config=config,
        order=_order(db, tenant_id, order_id),
        code=body.code,
        action="verify_delivery_code",
    )
