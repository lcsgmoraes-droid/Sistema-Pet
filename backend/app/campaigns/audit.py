from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services.business_audit_service import log_business_event


logger = logging.getLogger(__name__)


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", str(value))


def _money(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(Decimal(str(value or 0)).quantize(Decimal("0.01")))
    except Exception:
        return None


def _iso(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _serializable_id(value: Any) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


def _coupon_value(coupon: Any) -> tuple[str | None, float | None]:
    discount_value = getattr(coupon, "discount_value", None)
    discount_percent = getattr(coupon, "discount_percent", None)
    if discount_value is not None:
        return "fixed", _money(discount_value)
    if discount_percent is not None:
        try:
            return "percent", float(discount_percent)
        except (TypeError, ValueError):
            return "percent", None
    return None, None


def build_coupon_audit_metadata(
    coupon: Any,
    *,
    source: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value_kind, value = _coupon_value(coupon)
    metadata = {
        "coupon_id": _serializable_id(getattr(coupon, "id", None)),
        "coupon_code": getattr(coupon, "code", None),
        "campaign_id": _serializable_id(getattr(coupon, "campaign_id", None)),
        "customer_id": _serializable_id(getattr(coupon, "customer_id", None)),
        "coupon_type": _enum_value(getattr(coupon, "coupon_type", None)),
        "coupon_value_kind": value_kind,
        "coupon_value": value,
        "channel": _enum_value(getattr(coupon, "channel", None)),
        "status": _enum_value(getattr(coupon, "status", None)),
        "valid_until": _iso(getattr(coupon, "valid_until", None)),
        "min_purchase_value": _money(getattr(coupon, "min_purchase_value", None)),
        "source": source,
        "meta": dict(getattr(coupon, "meta", None) or {}),
    }
    metadata.update(extra or {})
    return metadata


def build_coupon_redemption_audit_metadata(
    *,
    coupon: Any | None,
    redemption: Any,
    reason: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = {
        "coupon_id": _serializable_id(
            getattr(redemption, "coupon_id", None) or getattr(coupon, "id", None)
        ),
        "coupon_code": getattr(coupon, "code", None),
        "campaign_id": _serializable_id(getattr(coupon, "campaign_id", None)),
        "customer_id": _serializable_id(
            getattr(redemption, "customer_id", None)
            or getattr(coupon, "customer_id", None)
        ),
        "redemption_id": _serializable_id(getattr(redemption, "id", None)),
        "venda_id": _serializable_id(getattr(redemption, "venda_id", None)),
        "discount_applied": _money(getattr(redemption, "discount_applied", None)),
        "redeemed_at": _iso(getattr(redemption, "redeemed_at", None)),
        "voided_at": _iso(getattr(redemption, "voided_at", None)),
        "voided_reason": getattr(redemption, "voided_reason", None),
        "reason": reason,
    }
    metadata.update(extra or {})
    return metadata


def build_loyalty_stamp_audit_metadata(
    *,
    stamp: Any,
    campaign: Any | None = None,
    operation: str,
    balance: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = {
        "stamp_id": _serializable_id(getattr(stamp, "id", None)),
        "campaign_id": _serializable_id(getattr(stamp, "campaign_id", None)),
        "campaign_name": getattr(campaign, "name", None) if campaign else None,
        "campaign_type": _enum_value(getattr(campaign, "campaign_type", None))
        if campaign
        else None,
        "customer_id": _serializable_id(getattr(stamp, "customer_id", None)),
        "venda_id": _serializable_id(getattr(stamp, "venda_id", None)),
        "stamp_index": _serializable_id(getattr(stamp, "stamp_index", None)),
        "is_manual": bool(getattr(stamp, "is_manual", False)),
        "operation": operation,
        "notes": getattr(stamp, "notes", None),
        "voided_at": _iso(getattr(stamp, "voided_at", None)),
        "balance": balance or {},
    }
    metadata.update(extra or {})
    return metadata


def log_campaign_event(
    *,
    db: Session,
    tenant_id: Any,
    event: str,
    entity_type: str,
    entity_id: int | None,
    metadata: dict[str, Any] | None = None,
    user_id: int | None = None,
    old_value: dict[str, Any] | None = None,
    details: str | None = None,
):
    try:
        return log_business_event(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            event=event,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
            old_value=old_value,
            details=details or event,
            commit=False,
        )
    except Exception as exc:
        logger.warning(
            "campaign_audit_failed event=%s entity_type=%s entity_id=%s error=%s",
            event,
            entity_type,
            entity_id,
            exc,
        )
        return None
