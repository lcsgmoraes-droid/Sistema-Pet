from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.middlewares.request_context import get_request_id
from app.utils.logger import logger as structured_logger


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


def _to_serializable_id(value: Any) -> str | int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return str(value)


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


def build_user_access_metadata(
    *,
    actor: Any,
    target_user: Any,
    tenant_id: Any,
    role: Any | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = {
        "actor_user_id": getattr(actor, "id", None),
        "actor_email": getattr(actor, "email", None),
        "target_user_id": getattr(target_user, "id", None),
        "target_email": getattr(target_user, "email", None),
        "tenant_id": _to_serializable_id(tenant_id),
        "role_id": getattr(role, "id", None) if role else None,
        "role_name": getattr(role, "name", None) if role else None,
    }
    metadata.update(extra or {})
    return metadata


def build_module_activation_metadata(
    *,
    tenant: Any,
    module: str,
    previous_modules: list[str],
    current_modules: list[str],
    subscription_created: bool,
) -> dict[str, Any]:
    return {
        "tenant_id": _to_serializable_id(getattr(tenant, "id", None)),
        "tenant_plan": getattr(tenant, "plan", None),
        "module": module,
        "previous_modules": sorted(previous_modules),
        "current_modules": sorted(current_modules),
        "subscription_created": subscription_created,
    }


def build_plan_activation_metadata(
    *,
    tenant: Any,
    previous_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "tenant_id": _to_serializable_id(getattr(tenant, "id", None)),
        "previous": previous_state,
        "current": {
            "plan": getattr(tenant, "plan", None),
            "billing_status": getattr(tenant, "billing_status", None),
            "subscription_source": getattr(tenant, "subscription_source", None),
            "subscription_activated_at": getattr(tenant, "subscription_activated_at", None).isoformat()
            if getattr(tenant, "subscription_activated_at", None)
            else None,
            "trial_started_at": getattr(tenant, "trial_started_at", None).isoformat()
            if getattr(tenant, "trial_started_at", None)
            else None,
            "trial_ends_at": getattr(tenant, "trial_ends_at", None).isoformat()
            if getattr(tenant, "trial_ends_at", None)
            else None,
        },
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
    action = _audit_action(event)
    request_id = get_request_id()
    redacted_metadata = _redact(metadata or {})
    payload = {
        "event": event,
        "request_id": request_id,
        "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metadata": redacted_metadata,
    }

    audit_row = log_action(
        db=db,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=_redact(old_value or {}) or None,
        new_value=payload,
        details=details or event,
        tenant_id=tenant_id,
        commit=commit,
    )
    try:
        structured_logger.info(
            "business_event",
            "Business audit event recorded",
            business_event=event,
            request_id=request_id,
            tenant_id=_to_serializable_id(tenant_id),
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            metadata=redacted_metadata,
            commit=commit,
        )
    except Exception:
        pass
    return audit_row
