"""PostgreSQL Row-Level Security tenant context helpers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import event, text
from sqlalchemy.orm import Session as ORMSession

from app.tenancy.context import get_current_tenant


RLS_TENANT_SETTING = "app.tenant_id"
_SET_CONFIG_SQL = text("SELECT set_config(:setting_name, :setting_value, true)")
_UNSET = object()


def _dialect_name(db: ORMSession) -> str:
    bind = db.get_bind()
    return str(bind.dialect.name)


def _resolve_tenant_value(tenant_id: Any) -> str:
    resolved = get_current_tenant() if tenant_id is _UNSET else tenant_id
    if resolved is None or resolved == "":
        return ""
    return str(UUID(str(resolved)))


def sync_rls_tenant(db: ORMSession, tenant_id: Any = _UNSET) -> bool:
    """
    Sync the Python tenant context into PostgreSQL transaction-local settings.

    RLS policies can read this with ``current_setting('app.tenant_id', true)``.
    The setting is transaction-local (third set_config argument = true), so it
    does not leak through pooled connections after commit/rollback.
    """
    if _dialect_name(db) != "postgresql":
        return False

    db.connection().execute(
        _SET_CONFIG_SQL,
        {
            "setting_name": RLS_TENANT_SETTING,
            "setting_value": _resolve_tenant_value(tenant_id),
        },
    )
    return True


def _sync_rls_before_flush(session, flush_context, instances) -> None:
    sync_rls_tenant(session, get_current_tenant())


def _registered_listeners(event_name: str):
    return list(getattr(ORMSession.dispatch, event_name)._clslevel.get(ORMSession, ()))


def register_rls_hooks_once() -> None:
    """Register RLS session hooks once, including after module reloads."""
    for listener in _registered_listeners("before_flush"):
        same_hook = (
            getattr(listener, "__module__", None) == __name__
            and getattr(listener, "__name__", None) == "_sync_rls_before_flush"
        )
        if same_hook and listener is not _sync_rls_before_flush:
            event.remove(ORMSession, "before_flush", listener)

    if not event.contains(ORMSession, "before_flush", _sync_rls_before_flush):
        event.listen(ORMSession, "before_flush", _sync_rls_before_flush)


register_rls_hooks_once()
