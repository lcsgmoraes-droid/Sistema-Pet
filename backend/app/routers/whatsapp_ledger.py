"""Consumo de mensagens de WhatsApp da propria loja (livro-razao)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.security.permissions_decorator import require_permission_dependency
from app.whatsapp.ledger_service import (
    listar_mensagens,
    periodo_do_mes,
    resumo_do_periodo,
)
from app.whatsapp.tenant_context import whatsapp_tenant_context

router = APIRouter(
    prefix="/whatsapp/ledger",
    tags=["WhatsApp - consumo"],
    dependencies=[Depends(require_permission_dependency("crm.configurar"))],
)


def _periodo(mes: str | None):
    try:
        return periodo_do_mes(mes)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.get("/resumo")
async def resumo(
    mes: str | None = Query(None, description="AAAA-MM; vazio = mês atual"),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> dict[str, Any]:
    _, tenant_id = user_and_tenant
    inicio, fim = _periodo(mes)
    with whatsapp_tenant_context(tenant_id):
        return resumo_do_periodo(db, tenant_id, inicio, fim)


@router.get("/mensagens")
async def mensagens(
    mes: str | None = Query(None, description="AAAA-MM; vazio = mês atual"),
    limite: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> dict[str, Any]:
    _, tenant_id = user_and_tenant
    inicio, fim = _periodo(mes)
    with whatsapp_tenant_context(tenant_id):
        return {"items": listar_mensagens(db, tenant_id, inicio, fim, limite)}
