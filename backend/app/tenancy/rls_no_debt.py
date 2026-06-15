"""Audit helpers for the final PostgreSQL RLS ratchet."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


INTENTIONALLY_GLOBAL_NO_RLS_TABLES = frozenset(
    {
        "bling_pedido_webhook_events",
        "campaign_event_queue",
        "notification_queue",
        "ops_alerts",
        "ops_error_events",
        "user_sessions",
    }
)


TENANT_ID_TABLES_WITHOUT_RLS_SQL = text(
    """
    SELECT c.relname AS table_name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'
      AND c.relname NOT LIKE 'pg_%'
      AND c.relname NOT LIKE 'sql_%'
      AND EXISTS (
          SELECT 1
          FROM information_schema.columns col
          WHERE col.table_schema = 'public'
            AND col.table_name = c.relname
            AND col.column_name = 'tenant_id'
      )
      AND NOT c.relrowsecurity
    ORDER BY c.relname
    """
)


def tenant_id_tables_without_rls(db: Session) -> list[str]:
    rows = db.execute(TENANT_ID_TABLES_WITHOUT_RLS_SQL).all()
    return [str(row[0]) for row in rows]


def unexpected_tenant_id_tables_without_rls(db: Session) -> list[str]:
    tables = set(tenant_id_tables_without_rls(db))
    return sorted(tables - INTENTIONALLY_GLOBAL_NO_RLS_TABLES)


def assert_no_unexpected_no_rls_tables(db: Session) -> list[str]:
    unexpected = unexpected_tenant_id_tables_without_rls(db)
    if unexpected:
        allowed = ", ".join(sorted(INTENTIONALLY_GLOBAL_NO_RLS_TABLES))
        found = ", ".join(unexpected)
        raise RuntimeError(
            "Unexpected tenant_id table(s) without PostgreSQL RLS: "
            f"{found}. Only intentional globals may remain without RLS: {allowed}."
        )
    return unexpected
