"""Ações individuais de relacionamento para aniversários."""

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
from app.produtos_models import AniversarioContato
from app.services.app_notifications import resolve_customer_app_user_id
from app.services.lembretes_aniversarios import (
    BirthdayTarget,
    get_birthday_target,
    list_birthday_contacts,
    list_upcoming_birthdays,
)
from app.services.lembretes_relacionamento import queue_status_value

router = APIRouter(prefix="/lembretes/aniversarios", tags=["lembretes-aniversarios"])


class BirthdayContactRequest(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    chave_cliente: UUID


def _clean_message(value: str) -> str:
    message = str(value or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="Informe a mensagem do contato")
    return message


def _target_or_404(db, *, tenant_id, birthday_type: str, reference_id: int):
    target = get_birthday_target(
        db,
        tenant_id=tenant_id,
        birthday_type=birthday_type,
        reference_id=reference_id,
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Aniversariante não encontrado")
    return target


def _serialize_contact(contact, *, queue=None) -> dict:
    status = queue_status_value(queue) or contact.status
    queue_results = {
        "enviado": "Notificação enviada pelo aplicativo",
        "falhou": "Falha no envio da notificação",
        "ignorado": "Envio ignorado por falta de destino válido",
        "pendente": "Notificação aguardando envio",
    }
    return {
        "id": contact.id,
        "tipo_aniversario": contact.tipo,
        "canal": contact.canal,
        "acao": contact.acao,
        "status": status,
        "mensagem": contact.mensagem,
        "resultado": (
            queue_results.get(status, contact.resultado)
            if queue is not None
            else contact.resultado
        ),
        "operador_nome": getattr(getattr(contact, "operador", None), "nome", None),
        "criado_em": contact.created_at.isoformat() if contact.created_at else None,
    }


def _new_contact(
    *,
    target: BirthdayTarget,
    tenant_id,
    user_id: int,
    channel: str,
    action: str,
    status: str,
    message: str,
    result: str,
    key: str,
    queue_id: int | None = None,
):
    return AniversarioContato(
        tenant_id=tenant_id,
        tipo=target.tipo,
        cliente_id=target.cliente.id,
        pet_id=target.pet.id if target.pet is not None else None,
        aniversario_em=target.aniversario_em,
        usuario_id=user_id,
        notification_queue_id=queue_id,
        canal=channel,
        acao=action,
        status=status,
        mensagem=message,
        resultado=result,
        idempotency_key=key,
    )


@router.get("", summary="Listar próximos aniversários de tutores e pets")
async def listar_aniversariantes(
    dias: int = Query(30, ge=0, le=90),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _, tenant_id = user_and_tenant
    return list_upcoming_birthdays(db, tenant_id=tenant_id, days=dias)


@router.get(
    "/{tipo}/{referencia_id}/contatos",
    summary="Histórico de contatos do aniversário",
)
async def listar_contatos_aniversario(
    tipo: str,
    referencia_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _, tenant_id = user_and_tenant
    target = _target_or_404(
        db, tenant_id=tenant_id, birthday_type=tipo, reference_id=referencia_id
    )
    contacts = list_birthday_contacts(db, tenant_id=tenant_id, target=target)
    return {"total": len(contacts), "contatos": contacts}


@router.post(
    "/{tipo}/{referencia_id}/contatos/whatsapp",
    summary="Registrar abertura de conversa de aniversário no WhatsApp",
)
async def registrar_whatsapp_aniversario(
    tipo: str,
    referencia_id: int,
    payload: BirthdayContactRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    target = _target_or_404(
        db, tenant_id=tenant_id, birthday_type=tipo, reference_id=referencia_id
    )
    phone = target.cliente.celular or target.cliente.telefone
    if not phone:
        raise HTTPException(status_code=422, detail="Cliente não possui telefone")
    if not can_send_marketing_whatsapp(
        db, tenant_id=tenant_id, customer_id=target.cliente.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Cliente não autorizou contatos de marketing pelo WhatsApp",
        )

    key = (
        f"birthday_whatsapp:{tenant_id}:{tipo}:{referencia_id}:"
        f"{target.aniversario_em}:{payload.chave_cliente}"
    )
    existing = (
        db.query(AniversarioContato)
        .filter(
            AniversarioContato.tenant_id == tenant_id,
            AniversarioContato.idempotency_key == key,
        )
        .first()
    )
    if existing:
        return _serialize_contact(existing)

    contact = _new_contact(
        target=target,
        tenant_id=tenant_id,
        user_id=current_user.id,
        channel="whatsapp",
        action="conversa_aberta",
        status="aberto",
        message=_clean_message(payload.mensagem),
        result="WhatsApp aberto; envio não confirmado pelo sistema",
        key=key,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _serialize_contact(contact)


@router.post(
    "/{tipo}/{referencia_id}/notificar-app",
    summary="Enfileirar notificação manual de aniversário no aplicativo",
)
async def notificar_aniversario_no_app(
    tipo: str,
    referencia_id: int,
    payload: BirthdayContactRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    current_user, tenant_id = user_and_tenant
    target = _target_or_404(
        db, tenant_id=tenant_id, birthday_type=tipo, reference_id=referencia_id
    )
    if not resolve_customer_app_user_id(
        db, tenant_id=tenant_id, cliente=target.cliente
    ):
        raise HTTPException(
            status_code=422,
            detail="Cliente ainda não possui uma conta vinculada no aplicativo",
        )
    if not can_send_marketing_push(
        db, tenant_id=tenant_id, customer_id=target.cliente.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Cliente não autorizou notificações de marketing no aplicativo",
        )

    message = _clean_message(payload.mensagem)
    queue_key = (
        f"birthday_manual:{tenant_id}:{tipo}:{referencia_id}:"
        f"{target.aniversario_em}:{payload.chave_cliente}"
    )
    queued = enqueue_push(
        db,
        tenant_id=tenant_id,
        customer_id=target.cliente.id,
        subject=(
            f"Aniversário do {target.pet.nome}"
            if target.pet is not None
            else "Feliz aniversário!"
        ),
        body=message,
        idempotency_key=queue_key,
        source="campaign",
        kind="birthday_pet" if target.pet is not None else "birthday_customer",
        payload={
            "target": "benefits",
            "customer_id": target.cliente.id,
            "pet_id": target.pet.id if target.pet is not None else None,
            "manual": True,
        },
    )
    if not queued:
        raise HTTPException(status_code=409, detail="Notificação já enfileirada")
    db.flush()
    queue = (
        db.query(NotificationQueue)
        .filter(
            NotificationQueue.tenant_id == tenant_id,
            NotificationQueue.idempotency_key == queue_key,
        )
        .first()
    )
    contact = _new_contact(
        target=target,
        tenant_id=tenant_id,
        user_id=current_user.id,
        queue_id=queue.id if queue else None,
        channel="push",
        action="push_manual",
        status=queue_status_value(queue) or "pendente",
        message=message,
        result="Notificação enfileirada para envio",
        key=f"contact:{queue_key}",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _serialize_contact(contact, queue=queue)
