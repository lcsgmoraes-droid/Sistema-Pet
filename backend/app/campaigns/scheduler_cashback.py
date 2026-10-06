"""Job de expiração e alertas de cashback."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.tenancy.context import clear_current_tenant, set_current_tenant

DbFactory = Callable[[], Any]


def run_cashback_expiration_check(*, db_factory: DbFactory, logger) -> None:
    """
    Job diário (07:00): processa expiração de cashback em dois passos:
    1. Insere lançamentos negativos apenas para o saldo ainda não usado dos
       créditos cujo horário exato de vencimento já passou. Créditos já
       consumidos recebem apenas um marcador administrativo de valor zero.
    2. Envia alerta (e-mail ou push) para clientes com cashback expirando nos
       próximos X dias (configurável via scheduler_config / alerta_dias_expiracao_cashback)
    """
    from app.models import Tenant

    db = db_factory()
    try:
        now_utc = datetime.now(timezone.utc)
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

        tenants = db.query(Tenant).filter(Tenant.status == "active").all()

        for tenant in tenants:
            set_current_tenant(uuid.UUID(str(tenant.id)))
            try:
                expired_count, alerted_count = _process_cashback_expiration_for_tenant(
                    db,
                    tenant,
                    now_utc=now_utc,
                    today_start=today_start,
                    logger=logger,
                )
                db.commit()
                logger.info(
                    "[CashbackExpiration] tenant=%s: %d expirado(s), %d alertado(s)",
                    tenant.id,
                    expired_count,
                    alerted_count,
                )

            except Exception as tenant_exc:
                logger.exception(
                    "[CashbackExpiration] Erro no tenant %s: %s",
                    tenant.id,
                    tenant_exc,
                )
                db.rollback()
            finally:
                clear_current_tenant()

    except Exception as exc:
        logger.exception("[CashbackExpiration] Erro geral: %s", exc)
    finally:
        db.close()


def _process_cashback_expiration_for_tenant(
    db, tenant, *, now_utc, today_start, logger
) -> tuple[int, int]:
    alert_days = _cashback_alert_days(db, tenant.id)
    expired_due = _cashback_credits_expiring_today(db, tenant.id, now_utc)
    expired_count = sum(
        bool(_expire_cashback_credit_if_needed(db, tenant, tx, now_utc=now_utc))
        for tx in expired_due
    )

    expiring_soon = _cashback_credits_expiring_soon(
        db,
        tenant.id,
        today_end=now_utc,
        alert_limit=now_utc + timedelta(days=alert_days),
    )
    alerted = _send_cashback_expiration_alerts(
        db,
        tenant,
        expiring_soon,
        now_utc=now_utc,
        today_start=today_start,
        logger=logger,
    )
    return expired_count, len(alerted)


def _cashback_alert_days(db, tenant_id) -> int:
    from app.campaigns.models import Campaign, CampaignTypeEnum

    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.cashback,
        )
        .first()
    )
    params = campaign.params if campaign else {}
    return int(params.get("cashback_alerta_dias", 7))


def _cashback_credits_expiring_today(db, tenant_id, now_utc):
    """Load all due credits without an expiration debit or closure marker."""
    from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction

    expiration = aliased(CashbackTransaction)
    processed = (
        select(expiration.id)
        .where(
            expiration.tenant_id == CashbackTransaction.tenant_id,
            expiration.customer_id == CashbackTransaction.customer_id,
            expiration.source_type == CashbackSourceTypeEnum.expiration,
            expiration.source_id == CashbackTransaction.id,
        )
        .correlate(CashbackTransaction)
        .exists()
    )

    return (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.tx_type == "credit",
            CashbackTransaction.expires_at <= now_utc,
            ~processed,
        )
        .order_by(CashbackTransaction.expires_at, CashbackTransaction.id)
        .all()
    )


def _expire_cashback_credit_if_needed(db, tenant, tx, *, now_utc) -> bool:
    from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
    from app.campaigns.cashback_wallet import (
        get_cashback_wallet,
        lock_cashback_customer,
    )
    from app.campaigns.notification_service import enqueue_email
    from app.models import Cliente

    if tx.expires_at is None or tx.expires_at > now_utc:
        return False
    lock_cashback_customer(db, tenant_id=tenant.id, customer_id=tx.customer_id)
    already_expired = (
        db.query(CashbackTransaction.id)
        .filter(
            CashbackTransaction.tenant_id == tenant.id,
            CashbackTransaction.customer_id == tx.customer_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.expiration,
            CashbackTransaction.source_id == tx.id,
        )
        .first()
    )
    if already_expired:
        return False

    restante = get_cashback_wallet(
        db, tenant_id=tenant.id, customer_id=tx.customer_id, as_of=now_utc
    ).expected_expiration_by_credit.get(tx.id, 0)
    has_unspent_balance = restante > 0

    db.add(
        CashbackTransaction(
            tenant_id=tenant.id,
            customer_id=tx.customer_id,
            amount=-restante if has_unspent_balance else Decimal("0.00"),
            source_type=CashbackSourceTypeEnum.expiration,
            source_id=tx.id,
            description=(
                f"Expiração do saldo não utilizado #CBTX-{tx.id} "
                f"(R$ {float(restante):.2f})"
                if has_unspent_balance
                else f"Crédito #CBTX-{tx.id} totalmente utilizado; sem expiração de saldo"
            ),
            tx_type="expired" if has_unspent_balance else "closed",
        )
    )
    db.flush()
    if not has_unspent_balance:
        return False

    cliente = db.query(Cliente).filter(Cliente.id == tx.customer_id).first()
    if cliente:
        from app.campaigns.app_push import enqueue_campaign_push

        enqueue_campaign_push(
            db,
            tenant_id=tenant.id,
            customer_id=tx.customer_id,
            title="Seu cashback expirou",
            body=(
                f"Ola, {cliente.nome}! R$ {float(restante):.2f} de cashback "
                "venceu hoje."
            ),
            idempotency_key=f"cashback_expired:{tenant.id}:{tx.id}:push",
            kind="cashback_expired",
            campaign=None,
            payload={
                "target": "benefits",
                "customer_id": tx.customer_id,
                "cashback_amount": float(restante),
                "cashback_tx_id": tx.id,
            },
        )
    if cliente and cliente.email:
        enqueue_email(
            db,
            tenant_id=tenant.id,
            customer_id=tx.customer_id,
            subject="Seu cashback expirou hoje 😢",
            body=(
                f"Olá, {cliente.nome}! Infelizmente R$ {float(restante):.2f} "
                f"de cashback venceu hoje sem ser utilizado. "
                f"Continue comprando para acumular novos créditos!"
            ),
            email_address=cliente.email,
            idempotency_key=f"cashback_expired:{tenant.id}:{tx.id}:email",
        )
    return True


def _cashback_credits_expiring_soon(db, tenant_id, *, today_end, alert_limit):
    from app.campaigns.models import CashbackTransaction

    return (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.tx_type == "credit",
            CashbackTransaction.expires_at > today_end,
            CashbackTransaction.expires_at <= alert_limit,
        )
        .all()
    )


def _send_cashback_expiration_alerts(
    db, tenant, transactions, *, now_utc, today_start, logger
) -> set:
    alerted = set()
    for tx in transactions:
        if tx.customer_id in alerted:
            continue
        if _send_cashback_expiration_alert(
            db,
            tenant,
            tx,
            now_utc=now_utc,
            today_start=today_start,
            logger=logger,
        ):
            alerted.add(tx.customer_id)
    return alerted


def _send_cashback_expiration_alert(
    db, tenant, tx, *, now_utc, today_start, logger
) -> bool:
    from app.campaigns.models import NotificationQueue
    from app.campaigns.cashback_wallet import get_cashback_wallet
    from app.campaigns.notification_service import enqueue_email
    from app.models import Cliente

    restante = get_cashback_wallet(
        db, tenant_id=tenant.id, customer_id=tx.customer_id, as_of=now_utc
    ).remaining_by_credit.get(tx.id, 0)
    if restante <= 0:
        return False

    idem_key = (
        f"cashback_alerta:{tenant.id}:{tx.customer_id}:{today_start.date().isoformat()}"
    )
    already_alerted = (
        db.query(NotificationQueue.id)
        .filter(NotificationQueue.idempotency_key == idem_key)
        .first()
    )
    if already_alerted:
        return True

    cliente = db.query(Cliente).filter(Cliente.id == tx.customer_id).first()
    if not cliente:
        return False

    remaining_days = max(0, (tx.expires_at - now_utc).days)
    from app.campaigns.app_push import enqueue_campaign_push

    enqueue_campaign_push(
        db,
        tenant_id=tenant.id,
        customer_id=tx.customer_id,
        title="Cashback perto de vencer",
        body=(
            f"Ola, {cliente.nome}! Voce tem R$ {float(restante):.2f} "
            f"de cashback que vence em {remaining_days} dia(s)."
        ),
        idempotency_key=f"{idem_key}:push",
        kind="cashback_expiring",
        campaign=None,
        payload={
            "target": "benefits",
            "customer_id": tx.customer_id,
            "cashback_amount": float(restante),
            "cashback_tx_id": tx.id,
            "remaining_days": remaining_days,
        },
    )
    if cliente.email:
        enqueue_email(
            db,
            tenant_id=tenant.id,
            customer_id=tx.customer_id,
            subject=f"Seu cashback expira em {remaining_days} dia(s)! ⏰",
            body=(
                f"Olá, {cliente.nome}! Você tem R$ {float(restante):.2f} "
                f"de cashback que vai expirar em {remaining_days} dia(s). "
                f"Venha fazer uma compra e não perca seus créditos!"
            ),
            email_address=cliente.email,
            idempotency_key=idem_key,
        )
    logger.info(
        "[CashbackExpiration] Alerta enviado: tenant=%s customer=%d dias=%d",
        tenant.id,
        tx.customer_id,
        remaining_days,
    )
    return True
