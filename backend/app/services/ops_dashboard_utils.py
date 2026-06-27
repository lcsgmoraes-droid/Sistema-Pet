"""Helpers compartilhados do painel operacional."""

from datetime import datetime, timezone
import os
from typing import Any

from sqlalchemy.orm import Session

from app.models import Tenant


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _event_dt(event: dict[str, Any]) -> datetime | None:
    raw = str(event.get("created_at") or "")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _status_code(event: dict[str, Any]) -> int:
    try:
        return int(event.get("status_code") or 0)
    except (TypeError, ValueError):
        return 0


def _duration(event: dict[str, Any]) -> float:
    try:
        return float(event.get("duration_ms") or 0)
    except (TypeError, ValueError):
        return 0


def _latest_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return max(events, key=lambda event: _event_dt(event) or epoch, default=None)


def _event_payload_value(event: dict[str, Any] | None, key: str) -> Any:
    if not event:
        return None
    if key in event:
        return event.get(key)
    payload = event.get("payload")
    if isinstance(payload, dict):
        return payload.get(key)
    return None


def _event_time_text(event: dict[str, Any] | None) -> str | None:
    if not event:
        return None
    return (
        str(_event_payload_value(event, "created_at") or "")
        or str(event.get("started_at") or "")
        or str(event.get("last_seen_at") or "")
        or None
    )


def _tenant_names(db: Session, tenant_ids: set[str]) -> dict[str, str]:
    real_ids = {
        tenant_id for tenant_id in tenant_ids if tenant_id and tenant_id != "sem_tenant"
    }
    if not real_ids:
        return {}

    tenants = db.query(Tenant.id, Tenant.name).filter(Tenant.id.in_(real_ids)).all()
    return {str(tenant.id): tenant.name for tenant in tenants}
