"""Carteira piloto: consulta, orcamento e resultado. Sem endpoints de recarga."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.creditos_schemas import (
    CreditoOrcamentoRequest,
    SERVICE_PERMISSIONS,
    normalizar_credit_payload,
)
from app.db import get_session
from app.produtos_models import Produto
from app.security.permissions_decorator import check_permission, require_any_permission
from app.services import creditos_service
from app.services.creditos_catalog import CreditosError, get_catalog, get_creditos_mode
from app.services.creditos_execution import creditos_http_error
from app.tenancy.context import set_current_tenant

router = APIRouter(prefix="/creditos", tags=["Creditos CorePet"])
_ACCESS = tuple(SERVICE_PERMISSIONS.values())


def _check_service_permission(db, user, tenant_id, service_code):
    permission = SERVICE_PERMISSIONS.get(service_code)
    if permission is None:
        raise HTTPException(400, "Recurso nao disponivel.")
    set_current_tenant(tenant_id)
    check_permission(db, user.id, permission, tenant_id, current_user=user)


@router.get("/catalogo")
@require_any_permission(_ACCESS)
def catalogo(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    try:
        return get_catalog(user_and_tenant[1])
    except CreditosError as exc:
        raise creditos_http_error(exc) from exc


@router.get("/carteira")
@require_any_permission(_ACCESS)
def carteira(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    try:
        tenant_id = user_and_tenant[1]
        mode = get_creditos_mode(tenant_id)
        if mode == "off":
            return {
                "available_credits": 0,
                "reserved_credits": 0,
                "mode": mode,
                "checkout_enabled": False,
            }
        return {
            **creditos_service.get_wallet(db, tenant_id),
            "mode": mode,
            "checkout_enabled": False,
        }
    except CreditosError as exc:
        raise creditos_http_error(exc) from exc


@router.get("/extrato")
@require_any_permission(_ACCESS)
def extrato(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    try:
        tenant_id = user_and_tenant[1]
        if get_creditos_mode(tenant_id) == "off":
            return {"items": [], "limit": limit, "offset": offset}
        return creditos_service.get_ledger(db, tenant_id, limit=limit, offset=offset)
    except CreditosError as exc:
        raise creditos_http_error(exc) from exc


@router.post("/orcamento")
def orcamento(
    payload: CreditoOrcamentoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    _check_service_permission(db, user, tenant_id, payload.service_code)
    request_payload = normalizar_credit_payload(
        payload.service_code, payload.request_payload
    )
    if payload.service_code == "oferta.imagem":
        produto = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.id == request_payload["produto_id"],
            )
            .first()
        )
        if not produto:
            raise HTTPException(404, "Produto nao encontrado.")
    try:
        return creditos_service.quote(
            db,
            tenant_id,
            user.id,
            payload.service_code,
            request_payload,
            idempotency_key=payload.idempotency_key or str(uuid4()),
        )
    except CreditosError as exc:
        raise creditos_http_error(exc) from exc


@router.get("/operacoes/{operation_id}")
def operacao(
    operation_id: UUID,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    set_current_tenant(tenant_id)
    try:
        item = creditos_service.get_operation(db, tenant_id, user.id, str(operation_id))
    except CreditosError as exc:
        raise creditos_http_error(exc) from exc
    _check_service_permission(db, user, tenant_id, item["service_code"])
    return {
        "operation_id": item["operation_id"],
        "status": item["status"],
        "result": item.get("result_payload") if item["status"] == "completed" else None,
        "error": "A geracao falhou. Confira um novo orcamento para tentar novamente."
        if item["status"] == "failed"
        else None,
    }
