"""
Serviço de Notificações — Campaign Engine
==========================================

Responsabilidades:
- Enfileirar notificações push e e-mail em `notification_queue`
- Garantir idempotência pelo `idempotency_key` (UNIQUE no banco)
- Não commita — o commit fica no caller (engine ou handler)

Uso:
    from app.campaigns.notification_service import enqueue_push, enqueue_email

    sent = enqueue_push(
        db,
        tenant_id=campaign.tenant_id,
        customer_id=cliente.id,
        body="Feliz aniversário! Seu cupom: ANIV-XK92P3",
        idempotency_key=f"bday:{campaign.id}:{cliente.id}:{today}",
        push_token=cliente_push_token,
    )
"""

import logging

from sqlalchemy.orm import Session

from app.campaigns.models import (
    NotificationChannelEnum,
    NotificationQueue,
)

logger = logging.getLogger(__name__)


def enqueue_push(
    db: Session,
    *,
    tenant_id,
    customer_id: int,
    body: str,
    idempotency_key: str,
    push_token: str | None = None,
) -> bool:
    """
    Enfileira notificação push.

    Retorna True se a notificação foi adicionada à fila,
    False se a idempotency_key já estava registrada (skip silencioso).

    Não usa try/except + rollback para não quebrar a transação externa.
    Usa SELECT antes do INSERT para verificar duplicata.
    """
    existing = (
        db.query(NotificationQueue.id)
        .filter(NotificationQueue.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        logger.debug(
            "[notification_service] Push já enfileirado: key=%s", idempotency_key
        )
        return False

    notif = NotificationQueue(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        customer_id=customer_id,
        channel=NotificationChannelEnum.push,
        body=body,
        push_token=push_token,
    )
    db.add(notif)
    logger.debug(
        "[notification_service] Push enfileirado: key=%s customer_id=%d",
        idempotency_key,
        customer_id,
    )
    return True


def enqueue_email(
    db: Session,
    *,
    tenant_id,
    customer_id: int,
    subject: str,
    body: str,
    email_address: str,
    idempotency_key: str,
) -> bool:
    """
    Enfileira e-mail.

    Retorna True se adicionado, False se já existia (skip silencioso).
    Não precisa de commit — o caller gerencia a transação.
    """
    existing = (
        db.query(NotificationQueue.id)
        .filter(NotificationQueue.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        logger.debug(
            "[notification_service] E-mail já enfileirado: key=%s", idempotency_key
        )
        return False

    notif = NotificationQueue(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        customer_id=customer_id,
        channel=NotificationChannelEnum.email,
        subject=subject,
        body=body,
        email_address=email_address,
    )
    db.add(notif)
    logger.debug(
        "[notification_service] E-mail enfileirado: key=%s customer_id=%d",
        idempotency_key,
        customer_id,
    )
    return True
