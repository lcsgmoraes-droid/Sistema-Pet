import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


DEFAULT_REQUEST_DUE_DAYS = 15
COMPLETED_DELETION_SCRUB_NOTE = (
    "Solicitacao de exclusao concluida; dados pessoais do titular foram anonimizados."
)

PREFERENCE_TYPES = (
    "marketing_email",
    "marketing_whatsapp",
    "marketing_sms",
    "marketing_push",
    "analytics",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def json_dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=json_default)


def json_load(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except Exception:
        return None


__all__ = [
    "COMPLETED_DELETION_SCRUB_NOTE",
    "DEFAULT_REQUEST_DUE_DAYS",
    "PREFERENCE_TYPES",
    "iso",
    "json_default",
    "json_dump",
    "json_load",
    "num",
    "utcnow",
]
