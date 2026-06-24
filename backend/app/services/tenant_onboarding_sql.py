from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.tenant_onboarding_templates import (
    INSERT_TABLE_PATTERN,
    ITEM_INSTALL_TARGET_TABLES,
)
from app.utils.tenant_safe_sql import (
    execute_tenant_safe,
    execute_tenant_safe_scalar,
)


def _items_by_type(items: list[dict[str, Any]], item_type: str) -> list[dict[str, Any]]:
    return [item for item in items if item["item_type"] == item_type]


def _scalar(
    db: Session,
    sql: str,
    params: dict[str, Any],
    tenant_id: str,
    *,
    scalar_fn=execute_tenant_safe_scalar,
) -> Any:
    return scalar_fn(db, sql, params, tenant_id=tenant_id)


def _insert_target_table(sql: str) -> str | None:
    match = INSERT_TABLE_PATTERN.search(sql or "")
    if not match:
        return None
    table_name = match.group(1)
    if table_name not in ITEM_INSTALL_TARGET_TABLES:
        return None
    return table_name


def _sync_postgres_id_sequence(db: Session, table_name: str) -> None:
    """Keep legacy/imported rows from making nextval reuse an existing id."""
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    synced_tables = db.info.setdefault("tenant_onboarding_sequences_synced", set())
    if table_name in synced_tables:
        return

    sequence_name = db.execute(
        text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
        {"table_name": table_name},
    ).scalar()
    if not sequence_name:
        synced_tables.add(table_name)
        return

    db.execute(
        text(
            f"""
            SELECT CASE
                WHEN max_id IS NULL THEN setval(:sequence_name, 1, false)
                ELSE setval(:sequence_name, max_id, true)
            END
            FROM (SELECT MAX(id)::bigint AS max_id FROM {table_name}) seq_sync
            """
        ),
        {"sequence_name": sequence_name},
    )
    synced_tables.add(table_name)


def _execute_insert(
    db: Session,
    sql: str,
    params: dict[str, Any],
    tenant_id: str,
    *,
    execute_fn=execute_tenant_safe,
) -> None:
    target_table = _insert_target_table(sql)
    if target_table:
        _sync_postgres_id_sequence(db, target_table)

    execute_fn(
        db,
        sql,
        params,
        tenant_id=tenant_id,
        require_tenant=False,
    )
