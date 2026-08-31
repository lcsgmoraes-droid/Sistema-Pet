"""Acoes de relacionamento da central de lembretes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user_and_tenant
from app.campaigns.models import NotificationQueue
from app.campaigns.notification_service import (
    can_send_marketing_push,
    can_send_marketing_whatsapp,
    enqueue_push,
)
from app.db import get_session
from app.produtos_models import LembreteContato
from app.services.app_notifications import resolve_customer_app_user_id
from app.services.lembretes_relacionamento import (
    build_report,
    get_active_reminder,
    list_contacts,
    queue_status_value,
    serialize_contact,
)

router = APIRouter(prefix="/lembretes", tags=["lembretes-relacionamento"])


class ContatoRequest(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    chave_cliente: UUID


def _clean_message(value: str) -> str:
    message = str(value or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="Informe a mensagem do contato")
    return message


@router.get("/{lembrete_id}/contatos", summary="Historico de contatos do lembrete")
async def listar_contatos(
    lembrete_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _, tenant_id = user_and_tenant
    reminder = get_active_reminder(db, tenant_id=tenant_id, reminder_id=lembrete_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Lembrete ativo não encontrado")
    contacts = list_contacts(db, tenant_id=tenant_id, reminder_id=lembrete_id)
    return {"total": len(contacts), "contatos": contacts}


@router.post(
    "/{lembrete_id}/contatos/whatsapp",
    summary="Registrar abertura de conversa no WhatsApp",
)
async def registrar_contato_whatsapp(
    lembrete_id: int,
    payload: ContatoRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    reminder = get_active_reminder(db, tenant_id=tenant_id, reminder_id=lembrete_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Lembrete ativo não encontrado")
    phone = getattr(reminder.cliente, "celular", None) or getattr(
        reminder.cliente, "telefone", None
    )
    if not phone:
        raise HTTPException(status_code=422, detail="Cliente não possui telefone")
    if not can_send_marketing_whatsapp(
        db, tenant_id=tenant_id, customer_id=reminder.cliente_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Cliente não autorizou contatos de marketing pelo WhatsApp",
        )

    key = f"reminder_whatsapp:{tenant_id}:{lembrete_id}:{payload.chave_cliente}"
    existing = (
        db.query(LembreteContato)
        .filter(
            LembreteContato.tenant_id == tenant_id,
            LembreteContato.idempotency_key == key,
        )
        .first()
    )
    if existing:
        return serialize_contact(existing)

    contact = LembreteContato(
        tenant_id=tenant_id,
        lembrete_id=reminder.id,
        cliente_id=reminder.cliente_id,
        produto_id=reminder.produto_id,
        usuario_id=current_user.id,
        canal="whatsapp",
        acao="conversa_aberta",
        status="aberto",
        mensagem=_clean_message(payload.mensagem),
        resultado="WhatsApp aberto; envio não confirmado pelo sistema",
        idempotency_key=key,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return serialize_contact(contact)


@router.post(
    "/{lembrete_id}/notificar-app",
    summary="Enfileirar notificacao manual no aplicativo",
)
async def notificar_cliente_no_app(
    lembrete_id: int,
    payload: ContatoRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    reminder = get_active_reminder(db, tenant_id=tenant_id, reminder_id=lembrete_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Lembrete ativo não encontrado")

    app_user_id = resolve_customer_app_user_id(
        db, tenant_id=tenant_id, cliente=reminder.cliente
    )
    if not app_user_id:
        raise HTTPException(
            status_code=422,
            detail="Cliente ainda não possui uma conta vinculada no aplicativo",
        )
    if not can_send_marketing_push(
        db, tenant_id=tenant_id, customer_id=reminder.cliente_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Cliente não autorizou notificações de marketing no aplicativo",
        )

    today = datetime.utcnow().date().isoformat()
    queue_key = f"product_recurrence_manual:{tenant_id}:{lembrete_id}:{today}"
    existing_queue = (
        db.query(NotificationQueue)
        .filter(NotificationQueue.idempotency_key == queue_key)
        .first()
    )
    if existing_queue:
        raise HTTPException(
            status_code=409,
            detail="Já foi disparada uma notificação para este lembrete hoje",
        )

    message = _clean_message(payload.mensagem)
    queued = enqueue_push(
        db,
        tenant_id=tenant_id,
        customer_id=reminder.cliente_id,
        subject="Lembrete CorePet",
        body=message,
        idempotency_key=queue_key,
        source="product_recurrence",
        kind="repurchase_manual",
        payload={
            "target": "product",
            "reminder_id": reminder.id,
            "produto_id": reminder.produto_id,
            "product_id": reminder.produto_id,
        },
    )
    if not queued:
        raise HTTPException(status_code=409, detail="Notificação já enfileirada")
    db.flush()
    queue = (
        db.query(NotificationQueue)
        .filter(NotificationQueue.idempotency_key == queue_key)
        .first()
    )
    contact = LembreteContato(
        tenant_id=tenant_id,
        lembrete_id=reminder.id,
        cliente_id=reminder.cliente_id,
        produto_id=reminder.produto_id,
        usuario_id=current_user.id,
        notification_queue_id=queue.id if queue else None,
        canal="push",
        acao="push_manual",
        status=queue_status_value(queue) or "pendente",
        mensagem=message,
        resultado="Notificação enfileirada para envio",
        idempotency_key=f"contact:{queue_key}",
    )
    db.add(contact)
    reminder.notificacao_enviada = True
    reminder.data_notificacao_enviada = datetime.utcnow()
    reminder.status = "notificado"
    reminder.metodo_notificacao = "app"
    db.commit()
    db.refresh(contact)
    return serialize_contact(contact, queue)


@router.get("/relatorios/resumo", summary="Resumo de contatos e recompra")
async def resumo_relacionamento(
    dias: int = Query(30, ge=7, le=365),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _, tenant_id = user_and_tenant
    return build_report(db, tenant_id=tenant_id, days=dias)
