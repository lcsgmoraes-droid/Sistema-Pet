"""Creditos de WhatsApp da propria loja: saldo, pacotes avulsos e pedidos de compra."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.security.permissions_decorator import require_permission_dependency
from app.services.ops_whatsapp_creditos_service import (
    CreditosError,
    cancelar_compra,
    compra_para_dict,
    custos_para_lista,
    pacote_para_dict,
    solicitar_compra,
)
from app.whatsapp import creditos_service
from app.whatsapp.creditos_models import WhatsAppCompraPacote, WhatsAppPacote
from app.whatsapp.models import TenantWhatsAppConfig
from app.whatsapp.tenant_context import whatsapp_tenant_context

router = APIRouter(
    prefix="/whatsapp/creditos",
    tags=["WhatsApp - créditos"],
    dependencies=[Depends(require_permission_dependency("crm.configurar"))],
)

INSTRUCOES_PADRAO = (
    "Depois do pedido, nossa equipe envia os dados de pagamento e libera os créditos "
    "assim que o pagamento for confirmado."
)


class CompraPedido(BaseModel):
    pacote_id: int


def _executar(db: Session, acao):
    try:
        resultado = acao()
        db.commit()
        return resultado
    except CreditosError as erro:
        db.rollback()
        raise HTTPException(status_code=erro.status_code, detail=str(erro)) from erro


def _estado(db: Session, tenant_id: Any) -> dict[str, Any]:
    config = (
        db.query(TenantWhatsAppConfig)
        .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
        .first()
    )
    compras = (
        db.query(WhatsAppCompraPacote)
        .filter(WhatsAppCompraPacote.tenant_id == tenant_id)
        .order_by(WhatsAppCompraPacote.id.desc())
        .limit(20)
        .all()
    )
    return {
        "saldo": creditos_service.saldo(db, tenant_id, config),
        "custos": custos_para_lista(db),
        "pacotes": [
            pacote_para_dict(p)
            for p in db.query(WhatsAppPacote)
            .filter(WhatsAppPacote.ativo.is_(True))
            .order_by(WhatsAppPacote.creditos)
            .all()
        ],
        "compras": [compra_para_dict(c) for c in compras],
        "extrato": creditos_service.extrato(db, tenant_id),
        "instrucoes_de_pagamento": os.getenv("WHATSAPP_CREDITOS_INSTRUCOES", "").strip()
        or INSTRUCOES_PADRAO,
    }


@router.get("")
async def estado(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> dict[str, Any]:
    _, tenant_id = user_and_tenant
    with whatsapp_tenant_context(tenant_id):
        return _estado(db, tenant_id)


@router.post("/comprar", status_code=201)
async def comprar(
    dados: CompraPedido,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> dict[str, Any]:
    usuario, tenant_id = user_and_tenant
    with whatsapp_tenant_context(tenant_id):
        _executar(
            db,
            lambda: solicitar_compra(
                db,
                tenant_id=tenant_id,
                pacote_id=dados.pacote_id,
                solicitante=getattr(usuario, "email", None) or f"usuario {usuario.id}",
            ),
        )
        return _estado(db, tenant_id)


@router.post("/compras/{compra_id}/cancelar")
async def cancelar(
    compra_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> dict[str, Any]:
    _, tenant_id = user_and_tenant
    with whatsapp_tenant_context(tenant_id):
        _executar(db, lambda: cancelar_compra(db, compra_id, tenant_id=tenant_id))
        return _estado(db, tenant_id)
