"""Financial DEV: imports evidence only; never posts sales, cash or catalogues."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import get_session
from app.ifood_integration_models import IfoodMerchantConfig
from app.integrations.ifood.client import IfoodClientError
from app.integrations.ifood.financial_client import IfoodFinancialClient
from app.integrations.ifood.financial import (
    IfoodFinancialError,
    get_financial_report,
    import_financial_pages,
    record_order_costs,
)
from app.security.permissions_decorator import require_permission
from app.security import permissions_service

router = APIRouter(prefix="/integracoes/ifood/financeiro", tags=["iFood Financial DEV"])


class FinancialPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")
    begin_date: date
    end_date: date


Money = Decimal | None


class FinancialCosts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revenue: Money = Field(
        default=None, ge=0, max_digits=16, decimal_places=2, allow_inf_nan=False
    )
    cmv: Money = Field(
        default=None, ge=0, max_digits=16, decimal_places=2, allow_inf_nan=False
    )
    tax: Money = Field(
        default=None, ge=0, max_digits=16, decimal_places=2, allow_inf_nan=False
    )
    other_costs: Money = Field(
        default=None, ge=0, max_digits=16, decimal_places=2, allow_inf_nan=False
    )
    source_note: str = Field(min_length=5, max_length=1000)


def _require_dev():
    if str(settings.ENVIRONMENT).lower() not in {
        "development",
        "dev",
        "test",
        "homologation",
    }:
        raise HTTPException(
            409, "Financial desta entrega disponivel somente em DEV/homologacao."
        )


def _config(db, tenant_id):
    return (
        db.query(IfoodMerchantConfig)
        .filter(IfoodMerchantConfig.tenant_id == tenant_id)
        .first()
    )


def _merchant(db, tenant_id):
    config = _config(db, tenant_id)
    if not config or not config.merchant_id:
        raise HTTPException(
            409, "Vincule a loja iFood nas configuracoes antes da consulta financeira."
        )
    return config.merchant_id


def _read_status(db, tenant_id, user):
    config = _config(db, tenant_id)
    creds = bool(
        settings.IFOOD_CLIENT_ID.strip() and settings.IFOOD_CLIENT_SECRET.strip()
    )
    enabled = bool(settings.IFOOD_FINANCIAL_READ_ENABLED)
    merchant = bool(config and config.merchant_id)
    can_edit = True
    try:
        permissions_service.check_permission(
            db, user.id, "configuracoes.editar", tenant_id, current_user=user
        )
    except HTTPException as exc:
        if exc.status_code != 403:
            raise
        can_edit = False
    message = (
        "Consulta dos eventos de homologacao disponivel. O acesso Financial depende da autorizacao do iFood."
        if enabled and creds and merchant
        else "Consulta externa Financial aguardando habilitacao e credenciais de DEV; dados ja importados continuam disponiveis."
    )
    return dict(
        read_enabled=enabled,
        mode="homologation",
        homologation_only=True,
        can_sync=enabled and creds and merchant and can_edit,
        can_edit_costs=can_edit,
        merchant_configured=merchant,
        credentials_configured=creds,
        message=message,
    )


@router.get("/status")
@require_permission("relatorios.financeiro")
def status(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _require_dev()
    return _read_status(db, user_and_tenant[1], user_and_tenant[0])


@router.get("/relatorio")
@require_permission("relatorios.financeiro")
def report(
    begin_date: date,
    end_date: date,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _require_dev()
    try:
        return get_financial_report(
            db,
            user_and_tenant[1],
            _merchant(db, user_and_tenant[1]),
            begin_date,
            end_date,
        )
    except IfoodFinancialError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


@router.post("/sincronizar")
@require_permission("relatorios.financeiro")
@require_permission("configuracoes.editar")
def sync(
    body: FinancialPeriod,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _require_dev()
    user, tenant_id = user_and_tenant
    if not _read_status(db, tenant_id, user)["can_sync"]:
        raise HTTPException(
            409, "A consulta externa Financial ainda nao esta habilitada em DEV."
        )
    merchant = _merchant(db, tenant_id)
    try:
        with IfoodFinancialClient(
            client_id=settings.IFOOD_CLIENT_ID,
            client_secret=settings.IFOOD_CLIENT_SECRET,
            base_url=settings.IFOOD_API_BASE_URL,
            timeout_seconds=settings.IFOOD_REQUEST_TIMEOUT_SECONDS,
        ) as client:
            pages = client.fetch_financial_pages(
                merchant, body.begin_date, body.end_date
            )
        result = import_financial_pages(
            db,
            tenant_id,
            merchant,
            body.begin_date,
            body.end_date,
            pages,
            actor_id=user.id,
        )
        db.commit()
        return result
    except IfoodFinancialError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, str(exc)) from exc
    except IfoodClientError as exc:
        db.rollback()
        code = 429 if exc.status_code == 429 else 502
        raise HTTPException(code, str(exc)) from exc


@router.put("/pedidos/{order_id}/custos")
@require_permission("relatorios.financeiro")
@require_permission("configuracoes.editar")
def costs(
    order_id: str,
    body: FinancialCosts,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _require_dev()
    user, tenant_id = user_and_tenant
    if len(order_id) > 80 or not order_id.strip():
        raise HTTPException(422, "Identificador do pedido invalido.")
    try:
        result = record_order_costs(
            db,
            tenant_id,
            _merchant(db, tenant_id),
            order_id,
            body.model_dump(),
            actor_id=user.id,
        )
        db.commit()
        return result
    except IfoodFinancialError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, str(exc)) from exc
