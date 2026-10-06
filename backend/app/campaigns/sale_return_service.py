"""Reconcile purchase benefits inside the sale return transaction.

The sale row is the serialization point shared with CampaignEngine. Neither
this module nor the benefit services commit: the caller owns the transaction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.campaigns.audit import log_campaign_event
from app.campaigns.coupon_service import reverse_coupon_redemptions_for_sale
from app.campaigns.loyalty_service import (
    historical_stamp_value_for_sale,
    sync_loyalty_stamps_for_sale,
)
from app.campaigns.models import (
    Campaign,
    CampaignExecution,
    CashbackSourceTypeEnum,
    CashbackTransaction,
    Coupon,
    CouponStatusEnum,
    CampaignTypeEnum,
    LoyaltyStamp,
)
from app.vendas_devolucoes_models import VendaDevolucao

_CENT = Decimal("0.01")
_PURCHASE_STATUSES = frozenset(
    {
        "finalizada",
        "pago_nf",
        "baixa_parcial",
        "finalizada_devolucao",
        "finalizada_devolucao_parcial",
    }
)


def remaining_sale_amount(db: Session, *, tenant_id, venda) -> Decimal:
    """Return the retained sale value after all committed/visible return events."""
    returned = (
        db.query(func.sum(VendaDevolucao.valor_devolvido))
        .filter(
            VendaDevolucao.tenant_id == tenant_id,
            VendaDevolucao.venda_id == venda.id,
        )
        .scalar()
    )
    return max(
        Decimal("0"),
        Decimal(str(venda.total or 0)) - Decimal(str(returned or 0)),
    ).quantize(_CENT)


def prepare_purchase_event(db: Session, *, tenant_id, payload: dict) -> dict | None:
    """Lock the sale before a queued purchase event grants any benefit.

    A return holds the same sale lock. Whichever transaction commits first,
    the second one sees its result and grants/reconciles the correct net value.
    """
    from app.vendas_models import Venda

    venda_id = payload.get("venda_id")
    if not venda_id:
        return None
    venda = (
        db.query(Venda)
        .filter(Venda.id == int(venda_id), Venda.tenant_id == tenant_id)
        .with_for_update()
        .first()
    )
    if (
        venda is None
        or str(venda.status or "").lower() not in _PURCHASE_STATUSES
        or not venda.cliente_id
        or int(venda.cliente_id) != int(payload.get("customer_id") or 0)
    ):
        return None

    retained = remaining_sale_amount(db, tenant_id=tenant_id, venda=venda)
    if retained <= 0:
        return None
    return {
        **payload,
        "venda_total_original": float(venda.total or 0),
        "venda_total": float(retained),
        "customer_id": int(venda.cliente_id),
        "canal": venda.canal or payload.get("canal") or "loja_fisica",
    }


def _cashback_reversal_amount(
    *,
    grant: Decimal,
    reversed_amount: Decimal,
    expired_amount: Decimal,
    base_sale_total: Decimal,
    retained_sale_total: Decimal,
) -> Decimal:
    """How much of a grant is still unearned and has not already expired."""
    if grant <= 0 or base_sale_total <= 0:
        return Decimal("0.00")
    target = (
        grant * min(retained_sale_total / base_sale_total, Decimal("1"))
    ).quantize(_CENT)
    effective_now = max(grant - reversed_amount - expired_amount, Decimal("0"))
    effective_target = max(target - expired_amount, Decimal("0"))
    return max(effective_now - effective_target, Decimal("0")).quantize(_CENT)


def _reconcile_cashback(
    db: Session,
    *,
    tenant_id,
    venda,
    evento_devolucao,
    retained: Decimal,
) -> Decimal:
    from app.campaigns.cashback_wallet import (
        get_cashback_wallet,
        lock_cashback_customer,
    )

    # Keep a return, redemption and expiration on the same customer lock.
    lock_cashback_customer(db, tenant_id=tenant_id, customer_id=venda.cliente_id)
    remaining_by_credit = dict(
        get_cashback_wallet(
            db, tenant_id=tenant_id, customer_id=venda.cliente_id
        ).remaining_by_credit
    )
    executions = (
        db.query(CampaignExecution)
        .filter(
            CampaignExecution.tenant_id == tenant_id,
            CampaignExecution.customer_id == venda.cliente_id,
            CampaignExecution.reference_period == str(venda.id),
            CampaignExecution.reward_type == "cashback",
        )
        .all()
    )
    total_reversed = Decimal("0")
    for execution in executions:
        grants = (
            db.query(CashbackTransaction)
            .filter(
                CashbackTransaction.tenant_id == tenant_id,
                CashbackTransaction.customer_id == venda.cliente_id,
                CashbackTransaction.source_type == CashbackSourceTypeEnum.campaign,
                CashbackTransaction.source_id == execution.id,
            )
            .with_for_update()
            .all()
        )
        base = Decimal(
            str(
                (execution.reward_meta or {}).get("venda_total_base")
                or venda.total
                or 0
            )
        )
        for grant_tx in grants:
            adjustments = (
                db.query(CashbackTransaction)
                .filter(
                    CashbackTransaction.tenant_id == tenant_id,
                    CashbackTransaction.customer_id == venda.cliente_id,
                    CashbackTransaction.source_id == grant_tx.id,
                    CashbackTransaction.source_type.in_(
                        (
                            CashbackSourceTypeEnum.reversal,
                            CashbackSourceTypeEnum.expiration,
                        )
                    ),
                )
                .all()
            )
            reversed_amount = sum(
                (
                    -Decimal(str(tx.amount or 0))
                    for tx in adjustments
                    if tx.source_type == CashbackSourceTypeEnum.reversal
                ),
                Decimal("0"),
            )
            expired_amount = sum(
                (
                    -Decimal(str(tx.amount or 0))
                    for tx in adjustments
                    if tx.source_type == CashbackSourceTypeEnum.expiration
                ),
                Decimal("0"),
            )
            delta = _cashback_reversal_amount(
                grant=Decimal(str(grant_tx.amount or 0)),
                reversed_amount=reversed_amount,
                expired_amount=expired_amount,
                base_sale_total=base,
                retained_sale_total=retained,
            )
            # A used or expired part of this grant belongs to the customer;
            # a return may revoke only the amount still in this same lot.
            delta = min(delta, remaining_by_credit.get(grant_tx.id, Decimal("0.00")))
            if delta <= 0:
                continue
            remaining_by_credit[grant_tx.id] -= delta
            db.add(
                CashbackTransaction(
                    tenant_id=tenant_id,
                    customer_id=venda.cliente_id,
                    amount=-delta,
                    source_type=CashbackSourceTypeEnum.reversal,
                    source_id=grant_tx.id,
                    description=(
                        f"Estorno proporcional do cashback da venda #{venda.id} "
                        f"pela devolucao #{evento_devolucao.id}"
                    ),
                    tx_type="debit",
                )
            )
            total_reversed += delta
    db.flush()
    return total_reversed


def _reconcile_loyalty(
    db: Session,
    *,
    tenant_id,
    venda,
    retained: Decimal,
    evento_devolucao,
    validate_only: bool = False,
) -> dict[str, int]:
    stamps = (
        db.query(LoyaltyStamp)
        .filter(
            LoyaltyStamp.tenant_id == tenant_id,
            LoyaltyStamp.customer_id == venda.cliente_id,
            LoyaltyStamp.venda_id == venda.id,
            LoyaltyStamp.is_manual.is_(False),
        )
        .all()
    )
    result = {"stamps_voided": 0, "rewards_revoked": 0}
    prepared = []
    for campaign_id in sorted({stamp.campaign_id for stamp in stamps}):
        sale_stamps = [stamp for stamp in stamps if stamp.campaign_id == campaign_id]
        # A conferência manual pode ter estornado todos os carimbos legados.
        # Nesse caso não há benefício ativo da venda para recalcular ou reativar.
        if all(getattr(stamp, "voided_at", None) is not None for stamp in sale_stamps):
            continue
        try:
            historical_step = historical_stamp_value_for_sale(sale_stamps)
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Passo historico do cartao fidelidade nao comprovado "
                    "para esta venda. Concilie os carimbos antes da devolucao."
                ),
            ) from exc
        campaign = (
            db.query(Campaign)
            .filter(Campaign.tenant_id == tenant_id, Campaign.id == campaign_id)
            .first()
        )
        if campaign is None:
            raise HTTPException(
                status_code=409,
                detail="Campanha de fidelidade da venda nao encontrada; concilie manualmente.",
            )
        prepared.append((campaign, historical_step))
    if validate_only:
        return result
    for campaign, historical_step in prepared:
        synced = sync_loyalty_stamps_for_sale(
            db,
            campaign=campaign,
            customer_id=int(venda.cliente_id),
            venda_id=int(venda.id),
            venda_total=retained,
            reason=f"Devolucao #{evento_devolucao.id}",
            stamp_value_override=historical_step,
        )
        result["stamps_voided"] += synced["stamps_voided"]
        result["rewards_revoked"] += synced["revoked"]
    return result


def _reconcile_quick_repurchase(
    db: Session,
    *,
    tenant_id,
    venda,
    retained: Decimal,
    evento_devolucao,
    validate_only: bool = False,
) -> int:
    coupon_query = db.query(Coupon).filter(
        Coupon.tenant_id == tenant_id, Coupon.customer_id == venda.cliente_id
    )
    if not validate_only:
        coupon_query = coupon_query.with_for_update()
    coupons = coupon_query.all()
    linked = [
        coupon
        for coupon in coupons
        if (coupon.meta or {}).get("source_kind") == "quick_repurchase"
        and str((coupon.meta or {}).get("source_venda_id")) == str(venda.id)
    ]
    voided = 0
    campaigns = {}
    for coupon in coupons:
        if coupon.campaign_id not in campaigns:
            campaigns[coupon.campaign_id] = (
                (
                    db.query(Campaign)
                    .filter(
                        Campaign.tenant_id == tenant_id,
                        Campaign.id == coupon.campaign_id,
                    )
                    .first()
                )
                if coupon.campaign_id
                else None
            )

        campaign = campaigns[coupon.campaign_id]
        if (
            coupon not in linked
            and coupon.status in {CouponStatusEnum.active, CouponStatusEnum.used}
            and campaign is not None
            and campaign.campaign_type == CampaignTypeEnum.quick_repurchase
            and not (coupon.meta or {}).get("source_venda_id")
        ):
            sale_date = getattr(venda, "data_venda", None)
            coupon_date = getattr(coupon, "created_at", None)
            possibly_from_sale = (
                sale_date is None
                or coupon_date is None
                or coupon_date.date() >= sale_date.date()
            )
            if possibly_from_sale:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Cupom de recompra antigo sem venda de origem comprovada. "
                        "Concilie o beneficio antes de devolver a venda."
                    ),
                )

    to_void = []
    for coupon in linked:
        if coupon.status in {CouponStatusEnum.voided, CouponStatusEnum.expired}:
            continue
        threshold_raw = (coupon.meta or {}).get("min_purchase_value_snapshot")
        if retained > 0 and threshold_raw is None:
            raise HTTPException(
                status_code=409,
                detail="Minimo historico do cupom de recompra nao comprovado.",
            )
        try:
            threshold = Decimal(str(threshold_raw or 0))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=409,
                detail="Minimo historico do cupom de recompra invalido.",
            ) from exc
        if not threshold.is_finite() or threshold < 0:
            raise HTTPException(
                status_code=409,
                detail="Minimo historico do cupom de recompra invalido.",
            )
        if retained > 0 and retained >= threshold:
            continue
        if coupon.status == CouponStatusEnum.used:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Cupom de recompra concedido por esta venda ja foi usado. "
                    "Concilie o beneficio antes de devolver a venda."
                ),
            )
        to_void.append(coupon)
    if validate_only:
        return 0
    for coupon in to_void:
        coupon.status = CouponStatusEnum.voided
        coupon.meta = {
            **(coupon.meta or {}),
            "voided_reason": "venda_devolvida",
            "voided_at": datetime.now(timezone.utc).isoformat(),
            "source_devolucao_id": evento_devolucao.id,
        }
        log_campaign_event(
            db=db,
            tenant_id=tenant_id,
            event="campaign.coupon.voided",
            entity_type="campaign_coupons",
            entity_id=coupon.id,
            metadata={
                "source_venda_id": venda.id,
                "source_devolucao_id": evento_devolucao.id,
                "reason": "venda_devolvida",
            },
            details=f"Cupom {coupon.code} anulado apos devolucao da venda #{venda.id}",
        )
        voided += 1
    return voided


def preflight_purchase_benefits_on_return(
    db: Session,
    *,
    tenant_id,
    venda,
    valor_acumulado: Decimal,
) -> Decimal:
    """Validate historical benefit rules without changing ledger or rewards.

    The POST repeats this check while holding the sale lock. A preview may race
    with later changes, so it cannot replace the transactional POST validation.
    """
    retained = max(
        Decimal("0"),
        Decimal(str(venda.total or 0)) - Decimal(str(valor_acumulado or 0)),
    ).quantize(_CENT)
    if venda.cliente_id:
        _reconcile_loyalty(
            db,
            tenant_id=tenant_id,
            venda=venda,
            retained=retained,
            evento_devolucao=None,
            validate_only=True,
        )
        _reconcile_quick_repurchase(
            db,
            tenant_id=tenant_id,
            venda=venda,
            retained=retained,
            evento_devolucao=None,
            validate_only=True,
        )
    return retained


def reconcile_purchase_benefits_on_return(
    db: Session,
    *,
    tenant_id,
    venda,
    evento_devolucao,
    valor_acumulado: Decimal,
) -> dict:
    """Undo only benefits no longer earned after a partial or full return.

    The caller must hold the sale row lock and include the return event in the
    current transaction. No effect is committed independently.
    """
    retained = preflight_purchase_benefits_on_return(
        db, tenant_id=tenant_id, venda=venda, valor_acumulado=valor_acumulado
    )
    if not venda.cliente_id:
        coupon_reversal = (
            reverse_coupon_redemptions_for_sale(
                db,
                tenant_id=tenant_id,
                venda_id=venda.id,
                reason=f"Devolucao integral da venda #{venda.id}",
            )
            if retained <= 0
            else {"redemptions_voided": 0}
        )
        db.flush()
        return {
            "cashback_reversed": 0,
            "stamps_voided": 0,
            "rewards_revoked": 0,
            "coupons_voided": 0,
            "coupon_redemptions_reversed": coupon_reversal["redemptions_voided"],
        }
    cashback = _reconcile_cashback(
        db,
        tenant_id=tenant_id,
        venda=venda,
        evento_devolucao=evento_devolucao,
        retained=retained,
    )
    loyalty = _reconcile_loyalty(
        db,
        tenant_id=tenant_id,
        venda=venda,
        retained=retained,
        evento_devolucao=evento_devolucao,
    )
    quick_voided = _reconcile_quick_repurchase(
        db,
        tenant_id=tenant_id,
        venda=venda,
        retained=retained,
        evento_devolucao=evento_devolucao,
    )
    coupon_reversal = (
        reverse_coupon_redemptions_for_sale(
            db,
            tenant_id=tenant_id,
            venda_id=venda.id,
            reason=f"Devolucao integral da venda #{venda.id}",
        )
        if retained <= 0
        else {"redemptions_voided": 0}
    )
    db.flush()
    return {
        "cashback_reversed": float(cashback),
        "stamps_voided": loyalty["stamps_voided"],
        "rewards_revoked": loyalty["rewards_revoked"],
        "coupons_voided": quick_voided,
        "coupon_redemptions_reversed": coupon_reversal["redemptions_voided"],
    }
