from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.campaigns.models import Coupon, CouponStatusEnum, CouponTypeEnum

_CODE_CHARS = string.ascii_uppercase + string.digits
_MONEY_CENTS = Decimal("0.01")


def _generate_code(prefix: str, length: int = 6) -> str:
    suffix = "".join(secrets.choice(_CODE_CHARS) for _ in range(length))
    return f"{prefix}-{suffix}"


def _as_decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(_MONEY_CENTS, rounding=ROUND_HALF_UP)


def _normalize_coupon_code(code: str | None) -> str:
    return str(code or "").strip().upper()


def _align_reference_datetime(target_dt: datetime, reference_dt: datetime) -> datetime:
    if target_dt.tzinfo is None and reference_dt.tzinfo is not None:
        return reference_dt.replace(tzinfo=None)
    if target_dt.tzinfo is not None and reference_dt.tzinfo is None:
        return reference_dt.replace(tzinfo=timezone.utc)
    return reference_dt


def _coupon_is_expired(coupon: Coupon, now_ref: datetime) -> bool:
    if not coupon.valid_until:
        return False
    aligned_now = _align_reference_datetime(coupon.valid_until, now_ref)
    return coupon.valid_until < aligned_now


def _calculate_coupon_discount(coupon: Coupon, venda_total: Any) -> Decimal:
    sale_total = _as_decimal(venda_total)
    if sale_total <= 0:
        return Decimal("0.00")

    if coupon.coupon_type == CouponTypeEnum.percent and coupon.discount_percent:
        percent = _as_decimal(coupon.discount_percent)
        return (sale_total * percent / Decimal("100")).quantize(
            _MONEY_CENTS,
            rounding=ROUND_HALF_UP,
        )

    if coupon.coupon_type == CouponTypeEnum.fixed and coupon.discount_value:
        return min(_as_decimal(coupon.discount_value), sale_total)

    return Decimal("0.00")


def _restored_coupon_status(coupon: Coupon, now_ref: datetime) -> CouponStatusEnum:
    if _coupon_is_expired(coupon, now_ref):
        return CouponStatusEnum.expired
    return CouponStatusEnum.active
