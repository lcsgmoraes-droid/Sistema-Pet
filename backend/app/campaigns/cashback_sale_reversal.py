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
    now = datetime.now(timezone.utc)
    wallet = get_cashback_wallet(
        db, tenant_id=tenant_id, customer_id=customer_id, as_of=now
    )
    redemptions = (
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
    credit_ids = {
        credit_id
        for redemption in redemptions
        for credit_id in wallet.allocations_by_debit.get(redemption.id, {})
    }
    credits = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.id.in_(credit_ids),
        )
        .all()
        if credit_ids
        else []
    )
    credits_by_id = {credit.id: credit for credit in credits}
    root_ids = {
        getattr(credit, "origin_credit_id", None) or credit.id for credit in credits
    }
    roots_by_id = {credit.id: credit for credit in credits if credit.id in root_ids}
    missing_roots = root_ids - roots_by_id.keys()
    if missing_roots:
        roots_by_id.update(
            {
                row.id: row
                for row in db.query(CashbackTransaction)
                .filter(
                    CashbackTransaction.tenant_id == tenant_id,
                    CashbackTransaction.customer_id == customer_id,
                    CashbackTransaction.id.in_(missing_roots),
                )
                .all()
            }
        )
    campaign_roots = {
        root_id: root
        for root_id, root in roots_by_id.items()
        if getattr(root, "source_type", None) == CashbackSourceTypeEnum.campaign
        and getattr(root, "source_id", None)
    }
    root_executions = {}
    if campaign_roots:
        root_executions = {
            row.id: row
            for row in db.query(CampaignExecution)
            .filter(
                CampaignExecution.tenant_id == tenant_id,
                CampaignExecution.id.in_(
                    root.source_id for root in campaign_roots.values()
                ),
            )
            .all()
        }

    def origin_active(credit) -> bool:
        root = roots_by_id.get(getattr(credit, "origin_credit_id", None) or credit.id)
        if root is None or root.id not in campaign_roots:
            return True
        execution = root_executions.get(root.source_id)
        return execution is not None and not (execution.reward_meta or {}).get(
            "cashback_sale_revoked"
        )

    for redemption in redemptions:
        already_reversed = (
            db.query(CashbackTransaction.id)
            .filter(
                CashbackTransaction.tenant_id == tenant_id,
                CashbackTransaction.customer_id == customer_id,
                CashbackTransaction.source_type == CashbackSourceTypeEnum.reversal,
                CashbackTransaction.source_id == redemption.id,
            )
            .first()
        )
        if already_reversed:
            continue
        allocations = wallet.allocations_by_debit.get(redemption.id, {})
        any_refund = False
        for credit_id, amount in allocations.items():
            credit = credits_by_id[credit_id]
            if not origin_active(credit):
                continue
            any_refund = True
            db.add(
                CashbackTransaction(
                    tenant_id=tenant_id,
                    customer_id=customer_id,
                    amount=amount,
                    source_type=CashbackSourceTypeEnum.reversal,
                    source_id=redemption.id,
                    origin_credit_id=(
                        getattr(credit, "origin_credit_id", None) or credit.id
                    ),
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
            # A zero-value row records that the redemption was examined. It is
            # never a spendable credit and prevents a retry from refunding it.
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
    db.flush()

    executions = (
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
    if not executions:
        return
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
    wallet = get_cashback_wallet(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        as_of=datetime.now(timezone.utc),
    )
    for credit in [*earned_credits, *refunded_descendants]:
        already_reversed = (
            db.query(CashbackTransaction.id)
            .filter(
                CashbackTransaction.tenant_id == tenant_id,
                CashbackTransaction.customer_id == customer_id,
                CashbackTransaction.source_type == CashbackSourceTypeEnum.reversal,
                CashbackTransaction.source_id == credit.id,
                CashbackTransaction.amount < 0,
            )
            .first()
        )
        if already_reversed:
            continue
        remaining = wallet.remaining_by_credit.get(credit.id, Decimal("0.00"))
        if remaining <= 0:
            continue
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
    for execution in executions:
        execution.reward_meta = {
            **(execution.reward_meta or {}),
            "cashback_sale_revoked": True,
            "cashback_sale_revoked_at": now.isoformat(),
        }


__all__ = ["reverse_cashback_for_sale"]
