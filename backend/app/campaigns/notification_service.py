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
from app.whatsapp.security import DataPrivacyConsent
from app.whatsapp.tenant_context import whatsapp_tenant_context

logger = logging.getLogger(__name__)


_CONSENT_ALIASES = {
    "marketing_email": ("marketing_email", "marketing"),
    "marketing_push": ("marketing_push", "marketing"),
    "marketing_whatsapp": ("marketing_whatsapp", "whatsapp", "marketing"),
    "marketing_sms": ("marketing_sms", "sms", "marketing"),
}


def _customer_allows_contact(
    db: Session,
    *,
    tenant_id,
    customer_id: int | None,
    consent_type: str,
) -> bool:
    """Return False only when the customer explicitly opted out."""
    if not customer_id:
        return True

    consent_types = _CONSENT_ALIASES.get(consent_type, (consent_type,))
    with whatsapp_tenant_context(tenant_id):
        latest = (
            db.query(DataPrivacyConsent)
            .filter(
                DataPrivacyConsent.tenant_id == str(tenant_id),
                DataPrivacyConsent.subject_type == "customer",
                DataPrivacyConsent.subject_id == str(customer_id),
                DataPrivacyConsent.consent_type.in_(consent_types),
            )
            .order_by(
                DataPrivacyConsent.created_at.desc(),
                DataPrivacyConsent.id.desc(),
            )
            .first()
        )

    if not latest:
        return True

    return bool(latest.consent_given) and latest.revoked_at is None


def can_send_marketing_email(
    db: Session, *, tenant_id, customer_id: int | None
) -> bool:
    return _customer_allows_contact(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        consent_type="marketing_email",
    )


def can_send_marketing_push(db: Session, *, tenant_id, customer_id: int | None) -> bool:
    return _customer_allows_contact(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        consent_type="marketing_push",
    )


def can_send_marketing_whatsapp(
    db: Session, *, tenant_id, customer_id: int | None
) -> bool:
    return _customer_allows_contact(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        consent_type="marketing_whatsapp",
    )


def can_send_marketing_sms(db: Session, *, tenant_id, customer_id: int | None) -> bool:
    return _customer_allows_contact(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        consent_type="marketing_sms",
    )


def enqueue_push(
    db: Session,
    *,
    tenant_id,
    customer_id: int,
    body: str,
    idempotency_key: str,
    push_token: str | None = None,
    privacy_customer_id: int | None = None,
) -> bool:
    """
    Enfileira notificação push.

    Retorna True se a notificação foi adicionada à fila,
    False se a idempotency_key já estava registrada (skip silencioso).

    Não usa try/except + rollback para não quebrar a transação externa.
    Usa SELECT antes do INSERT para verificar duplicata.
    """
    consent_customer_id = (
        privacy_customer_id if privacy_customer_id is not None else customer_id
    )
    if not can_send_marketing_push(
        db, tenant_id=tenant_id, customer_id=consent_customer_id
    ):
        logger.info(
            "[notification_service] Push bloqueado por preferencia LGPD: customer_id=%s key=%s",
            consent_customer_id,
            idempotency_key,
        )
        return False

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
    privacy_customer_id: int | None = None,
) -> bool:
    """
    Enfileira e-mail.

    Retorna True se adicionado, False se já existia (skip silencioso).
    Não precisa de commit — o caller gerencia a transação.
    """
    consent_customer_id = (
        privacy_customer_id if privacy_customer_id is not None else customer_id
    )
    if not can_send_marketing_email(
        db, tenant_id=tenant_id, customer_id=consent_customer_id
    ):
        logger.info(
            "[notification_service] E-mail bloqueado por preferencia LGPD: customer_id=%s key=%s",
            consent_customer_id,
            idempotency_key,
        )
        return False

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
