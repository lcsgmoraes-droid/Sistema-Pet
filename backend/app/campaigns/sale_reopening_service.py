"""Suspend sale-issued coupons during editing without erasing their history."""

from datetime import datetime, timezone

from sqlalchemy import String, cast

from app.campaigns.audit import log_campaign_event
from app.campaigns.models import Coupon, CouponStatusEnum


def void_quick_repurchase_coupons_for_sale(db, *, tenant_id, venda_id: int) -> int:
    """The caller owns the sale lock and transaction; redeemed coupons stay used."""
    coupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.status == CouponStatusEnum.active,
            Coupon.meta["source_kind"].astext == "quick_repurchase",
            cast(Coupon.meta["source_venda_id"].astext, String) == str(venda_id),
        )
        .with_for_update()
        .all()
    )
    voided = 0
    for coupon in coupons:
        meta = coupon.meta or {}
        if meta.get("source_kind") != "quick_repurchase" or str(
            meta.get("source_venda_id")
        ) != str(venda_id):
            continue
        coupon.status = CouponStatusEnum.voided
        coupon.meta = {
            **meta,
            "voided_reason": "venda_reaberta",
            "voided_at": datetime.now(timezone.utc).isoformat(),
        }
        log_campaign_event(
            db=db,
            tenant_id=tenant_id,
            event="campaign.coupon.voided",
            entity_type="campaign_coupons",
            entity_id=coupon.id,
            metadata={"source_venda_id": venda_id, "reason": "venda_reaberta"},
            details=f"Cupom {coupon.code} suspenso para edicao da venda #{venda_id}",
        )
        voided += 1
    return voided
