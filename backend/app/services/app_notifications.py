from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app import vendas_models as _vendas_models  # noqa: F401
from app.models import AppNotification, User


logger = logging.getLogger(__name__)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def resolve_customer_app_user_id(db: Session, *, tenant_id, cliente) -> int | None:
    """Resolve o usuario do app para um cliente, preferindo o e-mail do cadastro."""
    cliente_email = _clean_text(getattr(cliente, "email", None)).lower()
    if cliente_email:
        try:
            user = (
                db.query(User)
                .filter(
                    User.email == cliente_email,
                    User.tenant_id == tenant_id,
                )
                .first()
            )
            if getattr(user, "id", None):
                return int(user.id)
        except Exception:
            logger.exception(
                "[AppNotifications] Falha ao resolver usuario por email tenant_id=%s cliente_id=%s",
                tenant_id,
                getattr(cliente, "id", None),
            )

    user_id = getattr(cliente, "user_id", None)
    return int(user_id) if user_id else None


def criar_notificacao_app(
    db: Session,
    *,
    tenant_id,
    user_id: int | None,
    customer_id: int | None,
    title: str,
    body: str,
    source: str,
    kind: str,
    payload: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> AppNotification | None:
    if not user_id:
        return None
    if not hasattr(db, "add"):
        return None

    if idempotency_key:
        existing = (
            db.query(AppNotification)
            .filter(
                AppNotification.tenant_id == tenant_id,
                AppNotification.user_id == user_id,
                AppNotification.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing:
            return existing

    notification = AppNotification(
        tenant_id=tenant_id,
        user_id=user_id,
        customer_id=customer_id,
        title=title,
        body=body,
        source=source,
        kind=kind,
        payload=payload or {},
        idempotency_key=idempotency_key,
    )
    db.add(notification)
    return notification


def criar_notificacao_estoque_app(
    db: Session,
    *,
    tenant_id,
    cliente,
    produto,
    pendencia=None,
    user_id_override: int | None = None,
) -> AppNotification | None:
    produto_id = getattr(produto, "id", None)
    pendencia_id = getattr(pendencia, "id", None)
    user_id = user_id_override or resolve_customer_app_user_id(
        db, tenant_id=tenant_id, cliente=cliente
    )
    payload = {
        "source": "stock_waitlist",
        "kind": "stock_available",
        "produto_id": produto_id,
        "product_id": produto_id,
        "pendencia_id": pendencia_id,
    }
    idempotency_key = f"stock_waitlist:{pendencia_id}" if pendencia_id else None

    return criar_notificacao_app(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        customer_id=getattr(cliente, "id", None),
        title="Produto disponivel",
        body=f"{getattr(produto, 'nome', 'Produto')} voltou ao estoque. Confira no app antes que acabe.",
        source="stock_waitlist",
        kind="stock_available",
        payload=payload,
        idempotency_key=idempotency_key,
    )


def registrar_resultado_push_notificacao_app(
    notification: AppNotification | None,
    *,
    sent: bool,
    ticket_id: str | None = None,
    error: str | None = None,
) -> None:
    if notification is None:
        return

    if sent:
        notification.delivered_at = notification.delivered_at or datetime.now(
            timezone.utc
        )
        notification.push_ticket_id = ticket_id or notification.push_ticket_id
        notification.push_error = None
        return

    notification.push_error = error or notification.push_error
