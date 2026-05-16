from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.middlewares.request_context import get_request_id


_REDACTED = "***REDACTED***"
_SENSITIVE_KEY_PARTS = (
    "password",
    "senha",
    "token",
    "secret",
    "jwt",
    "authorization",
    "cookie",
    "apikey",
    "api_key",
)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (_REDACTED if _is_sensitive_key(str(key)) else _redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    return value


def _audit_action(event: str) -> str:
    return f"business.{event}"[:100]


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_manual_discount_amount(venda: Any) -> float:
    gross_discount = _to_float(getattr(venda, "desconto_valor", 0))
    coupon_discount = _to_float(getattr(venda, "cupom_discount_applied", 0))
    return max(round(gross_discount - coupon_discount, 2), 0.0)


def build_sale_coupon_redeemed_metadata(
    *,
    venda: Any,
    coupon_consumed: dict[str, Any],
) -> dict[str, Any]:
    return {
        "sale_number": getattr(venda, "numero_venda", None),
        "coupon_id": coupon_consumed.get("coupon_id"),
        "coupon_code": coupon_consumed.get("coupon_code") or coupon_consumed.get("code"),
        "redemption_id": coupon_consumed.get("redemption_id"),
        "discount_applied": _to_float(coupon_consumed.get("discount_applied")),
        "customer_id": getattr(venda, "cliente_id", None),
        "sale_total": _to_float(getattr(venda, "total", None)),
    }


def build_sale_reopened_metadata(
    *,
    venda: Any,
    previous_status: str,
    commissions_removed: int,
    coupon_reversal: dict[str, Any] | None = None,
    loyalty_void: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "sale_number": getattr(venda, "numero_venda", None),
        "previous_status": previous_status,
        "new_status": getattr(venda, "status", None),
        "commissions_removed": commissions_removed,
        "coupon_code": getattr(venda, "cupom_code", None),
        "customer_id": getattr(venda, "cliente_id", None),
        "sale_total": _to_float(getattr(venda, "total", None)),
        "coupon_reversal": coupon_reversal or {},
        "loyalty_void": loyalty_void or {},
    }


def log_business_event(
    *,
    db: Session,
    tenant_id: Any,
    user_id: int | None,
    event: str,
    entity_type: str,
    entity_id: int | None,
    metadata: dict[str, Any] | None = None,
    old_value: dict[str, Any] | None = None,
    details: str | None = None,
    commit: bool = False,
):
    payload = {
        "event": event,
        "request_id": get_request_id(),
        "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metadata": _redact(metadata or {}),
    }

    return log_action(
        db=db,
        user_id=user_id,
        action=_audit_action(event),
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=_redact(old_value or {}) or None,
        new_value=payload,
        details=details or event,
        tenant_id=tenant_id,
        commit=commit,
    )
