"""Compensações de cashback quando uma venda é cancelada ou reaberta."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.campaigns.cashback_wallet import get_cashback_wallet, lock_cashback_customer
from app.campaigns.models import (
    Campaign,
    CampaignExecution,
    CampaignTypeEnum,
    CashbackSourceTypeEnum,
    CashbackTransaction,
)


def reverse_cashback_for_sale(db, *, tenant_id, sale_id: int, customer_id: int) -> None:
    """Restore redeemed lots and revoke only unspent rewards from this sale.

    A refund keeps each consumed credit's original expiry. Every compensating
    transaction points at the transaction being reversed, so retries cannot
    create a second refund. The caller owns the surrounding sale transaction.
    """
    lock_cashback_customer(db, tenant_id=tenant_id, customer_id=customer_id)
    revoked_at = datetime.now(timezone.utc)
    _refund_sale_redemptions(
        db,
        tenant_id=tenant_id,
        sale_id=sale_id,
        customer_id=customer_id,
        as_of=revoked_at,
    )
    _revoke_sale_rewards(
        db,
        tenant_id=tenant_id,
        sale_id=sale_id,
        customer_id=customer_id,
        revoked_at=revoked_at,
    )


def _customer_transactions_by_id(db, *, tenant_id, customer_id, transaction_ids):
    if not transaction_ids:
        return []
    return (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.id.in_(transaction_ids),
        )
        .all()
    )


def _sale_redemptions(db, *, tenant_id, sale_id, customer_id):
    return (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.redemption,
            CashbackTransaction.source_id == sale_id,
        )
        .order_by(CashbackTransaction.created_at, CashbackTransaction.id)
        .all()
    )


def _allocated_credits(db, *, tenant_id, customer_id, redemptions, wallet):
    allocated_ids = {
        credit_id
        for redemption in redemptions
        for credit_id in wallet.allocations_by_debit.get(redemption.id, {})
    }
    return {
        credit.id: credit
        for credit in _customer_transactions_by_id(
            db,
            tenant_id=tenant_id,
            customer_id=customer_id,
            transaction_ids=allocated_ids,
        )
    }


def _origin_credits(db, *, tenant_id, customer_id, credits_by_id):
    origin_ids = {
        getattr(credit, "origin_credit_id", None) or credit.id
        for credit in credits_by_id.values()
    }
    origins = {
        credit_id: credit
        for credit_id, credit in credits_by_id.items()
        if credit_id in origin_ids
    }
    missing_ids = origin_ids - origins.keys()
    origins.update(
        {
            credit.id: credit
            for credit in _customer_transactions_by_id(
                db,
                tenant_id=tenant_id,
                customer_id=customer_id,
                transaction_ids=missing_ids,
            )
        }
    )
    return origins


def _revoked_campaign_origins(db, *, tenant_id, origins):
    campaign_origins = {
        credit_id: credit
        for credit_id, credit in origins.items()
        if getattr(credit, "source_type", None) == CashbackSourceTypeEnum.campaign
        and getattr(credit, "source_id", None)
    }
    if not campaign_origins:
        return set()
    executions_by_id = {
        execution.id: execution
        for execution in db.query(CampaignExecution)
        .filter(
            CampaignExecution.tenant_id == tenant_id,
            CampaignExecution.id.in_(
                credit.source_id for credit in campaign_origins.values()
            ),
        )
        .all()
    }
    return {
        credit_id
        for credit_id, credit in campaign_origins.items()
        if credit.source_id not in executions_by_id
        or (executions_by_id[credit.source_id].reward_meta or {}).get(
            "cashback_sale_revoked"
        )
    }


def _redemption_already_reversed(db, *, tenant_id, customer_id, redemption_id):
    return (
        db.query(CashbackTransaction.id)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.reversal,
            CashbackTransaction.source_id == redemption_id,
        )
        .first()
        is not None
    )


def _refund_redemption(
    db,
    *,
    tenant_id,
    sale_id,
    customer_id,
    redemption,
    allocations,
    credits_by_id,
    revoked_origin_ids,
):
    if _redemption_already_reversed(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        redemption_id=redemption.id,
    ):
        return

    any_refund = False
    for credit_id, amount in allocations.items():
        credit = credits_by_id[credit_id]
        origin_id = getattr(credit, "origin_credit_id", None) or credit.id
        if origin_id in revoked_origin_ids:
            continue
        any_refund = True
        db.add(
            CashbackTransaction(
                tenant_id=tenant_id,
                customer_id=customer_id,
                amount=amount,
                source_type=CashbackSourceTypeEnum.reversal,
                source_id=redemption.id,
                origin_credit_id=origin_id,
                expires_at=credit.expires_at,
                tx_type="credit",
                description=(
                    f"Estorno do resgate da venda #{sale_id}; "
                    f"crédito original #CBTX-{credit_id}"
                ),
            )
        )

    allocated = sum(allocations.values(), Decimal("0.00"))
    uncovered = -Decimal(str(redemption.amount)) - allocated
    if uncovered > 0:
        any_refund = True
        db.add(
            CashbackTransaction(
                tenant_id=tenant_id,
                customer_id=customer_id,
                amount=uncovered,
                source_type=CashbackSourceTypeEnum.reversal,
                source_id=redemption.id,
                tx_type="credit",
                description=f"Estorno do resgate da venda #{sale_id} sem lote histórico",
            )
        )
    if not any_refund:
        # A zero-value row prevents a retry from refunding this redemption.
        db.add(
            CashbackTransaction(
                tenant_id=tenant_id,
                customer_id=customer_id,
                amount=Decimal("0.00"),
                source_type=CashbackSourceTypeEnum.reversal,
                source_id=redemption.id,
                tx_type="closed",
                description=f"Resgate da venda #{sale_id} sem valor a restituir",
            )
        )


def _refund_sale_redemptions(db, *, tenant_id, sale_id, customer_id, as_of):
    wallet = get_cashback_wallet(
        db, tenant_id=tenant_id, customer_id=customer_id, as_of=as_of
    )
    redemptions = _sale_redemptions(
        db, tenant_id=tenant_id, sale_id=sale_id, customer_id=customer_id
    )
    credits_by_id = _allocated_credits(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        redemptions=redemptions,
        wallet=wallet,
    )
    origins = _origin_credits(
        db, tenant_id=tenant_id, customer_id=customer_id, credits_by_id=credits_by_id
    )
    revoked_origin_ids = _revoked_campaign_origins(
        db, tenant_id=tenant_id, origins=origins
    )
    for redemption in redemptions:
        _refund_redemption(
            db,
            tenant_id=tenant_id,
            sale_id=sale_id,
            customer_id=customer_id,
            redemption=redemption,
            allocations=wallet.allocations_by_debit.get(redemption.id, {}),
            credits_by_id=credits_by_id,
            revoked_origin_ids=revoked_origin_ids,
        )
    db.flush()


def _sale_cashback_executions(db, *, tenant_id, sale_id, customer_id):
    return (
        db.query(CampaignExecution)
        .join(Campaign, Campaign.id == CampaignExecution.campaign_id)
        .filter(
            CampaignExecution.tenant_id == tenant_id,
            CampaignExecution.customer_id == customer_id,
            CampaignExecution.reference_period == str(sale_id),
            CampaignExecution.reward_type == "cashback",
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.cashback,
        )
        .all()
    )


def _sale_reward_credits(db, *, tenant_id, customer_id, executions):
    earned_credits = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.campaign,
            CashbackTransaction.source_id.in_(
                [execution.id for execution in executions]
            ),
            CashbackTransaction.amount > 0,
        )
        .all()
    )
    original_ids = [credit.id for credit in earned_credits]
    refunded_descendants = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.origin_credit_id.in_(original_ids),
            CashbackTransaction.amount > 0,
        )
        .all()
        if original_ids
        else []
    )
    return [*earned_credits, *refunded_descendants]


def _revoke_credit_if_unspent(db, *, tenant_id, sale_id, customer_id, credit, wallet):
    # A prior partial return may have reversed only part of this lot. The
    # replayed remaining amount, under the customer lock, makes retries safe
    # while allowing a reopening to revoke the rest of that same reward.
    remaining = wallet.remaining_by_credit.get(credit.id, Decimal("0.00"))
    if remaining <= 0:
        return
    db.add(
        CashbackTransaction(
            tenant_id=tenant_id,
            customer_id=customer_id,
            amount=-remaining,
            source_type=CashbackSourceTypeEnum.reversal,
            source_id=credit.id,
            tx_type="debit",
            description=f"Estorno do cashback concedido na venda #{sale_id}",
        )
    )


def _revoke_sale_rewards(db, *, tenant_id, sale_id, customer_id, revoked_at):
    executions = _sale_cashback_executions(
        db, tenant_id=tenant_id, sale_id=sale_id, customer_id=customer_id
    )
    if not executions:
        return
    reward_credits = _sale_reward_credits(
        db, tenant_id=tenant_id, customer_id=customer_id, executions=executions
    )
    wallet = get_cashback_wallet(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        as_of=datetime.now(timezone.utc),
    )
    for credit in reward_credits:
        _revoke_credit_if_unspent(
            db,
            tenant_id=tenant_id,
            sale_id=sale_id,
            customer_id=customer_id,
            credit=credit,
            wallet=wallet,
        )
    for execution in executions:
        execution.reward_meta = {
            **(execution.reward_meta or {}),
            "cashback_sale_revoked": True,
            "cashback_sale_revoked_at": revoked_at.isoformat(),
        }


__all__ = ["reverse_cashback_for_sale"]
