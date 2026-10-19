"""Listagem de saldos e acompanhamento manual de contatos pelo WhatsApp."""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.cashback_crm_service import (
    create_contact,
    customer_snapshot,
    list_contacts,
    list_customers,
    serialize_contact,
    whatsapp_url,
)
from app.db import get_session
from app.security.permissions_decorator import require_permission


router = APIRouter(prefix="/cashback/clientes")
CrmStatus = Literal[
    "sem_contato",
    "conversa_aberta",
    "mensagem_enviada",
    "aguardando_retorno",
    "interessado",
    "retornar_depois",
    "concluido",
    "sem_interesse",
    "nao_contatar",
]


class WhatsappContactBody(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    chave_cliente: UUID


class FollowupBody(BaseModel):
    status: CrmStatus
    observacao: str | None = Field(default=None, max_length=2000)
    proximo_contato_em: date | None = None
    chave_cliente: UUID


@router.get("")
@require_permission("clientes.visualizar")
def listar_clientes_cashback(
    busca: str | None = Query(None, max_length=120),
    status: CrmStatus | None = None,
    retorno_pendente: bool = False,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    return list_customers(
        db,
        tenant_id=tenant_id,
        search=busca,
        crm_status=status,
        due_only=retorno_pendente,
        page=pagina,
        per_page=por_pagina,
    )


@router.get("/{cliente_id}/contatos")
@require_permission("clientes.visualizar")
def listar_historico_cashback(
    cliente_id: int,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    return list_contacts(
        db,
        tenant_id=tenant_id,
        customer_id=cliente_id,
        page=pagina,
        per_page=por_pagina,
    )


@router.post("/{cliente_id}/contatos/whatsapp")
@require_permission("clientes.editar")
def registrar_whatsapp_cashback(
    cliente_id: int,
    payload: WhatsappContactBody,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    contact = create_contact(
        db,
        tenant_id=tenant_id,
        customer_id=cliente_id,
        user=user,
        request_key=payload.chave_cliente,
        message=payload.mensagem,
    )
    return {
        "contato": serialize_contact(contact),
        "whatsapp_url": whatsapp_url(contact),
        "cliente": customer_snapshot(db, tenant_id=tenant_id, customer_id=cliente_id),
    }


@router.post("/{cliente_id}/acompanhamento")
@require_permission("clientes.editar")
def registrar_acompanhamento_cashback(
    cliente_id: int,
    payload: FollowupBody,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    contact = create_contact(
        db,
        tenant_id=tenant_id,
        customer_id=cliente_id,
        user=user,
        request_key=payload.chave_cliente,
        crm_status=payload.status,
        note=payload.observacao,
        next_contact=payload.proximo_contato_em,
    )
    return {
        "contato": serialize_contact(contact),
        "cliente": customer_snapshot(db, tenant_id=tenant_id, customer_id=cliente_id),
    }
