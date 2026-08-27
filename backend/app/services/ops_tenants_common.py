from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import inspect
from sqlalchemy.orm import Session

BUSINESS_TIMEZONE = ZoneInfo("America/Sao_Paulo")


class OpsTenantActionError(RuntimeError):
    """Erro de negocio seguro para as operacoes administrativas de empresas."""


def _table_exists(db: Session, table_name: str) -> bool:
    return inspect(db.connection()).has_table(table_name)


def _column_exists(db: Session, table_name: str, column_name: str) -> bool:
    if not _table_exists(db, table_name):
        return False
    return column_name in {
        column["name"] for column in inspect(db.connection()).get_columns(table_name)
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def _business_today() -> date:
    return datetime.now(BUSINESS_TIMEZONE).date()
