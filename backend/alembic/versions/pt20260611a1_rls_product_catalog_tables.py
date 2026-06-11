"""enable RLS on product catalog tenant tables

Revision ID: pt20260611a1
Revises: ps20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from alembic import op
import sqlalchemy as sa


revision = "pt20260611a1"
down_revision = "ps20260611a1"
branch_labels = None
depends_on = None


PRODUCT_CATALOG_TABLES = (
    "departamentos",
    "marcas",
    "categorias",
)

TENANT_SCOPE_SQL = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def _postgres():
    bind = op.get_bind()
    return bind if bind.dialect.name == "postgresql" else None


def _present_tables(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return {
        table_name
        for table_name in PRODUCT_CATALOG_TABLES
        if inspector.has_table(table_name)
    }


def _policy(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def _enable_statements(table_name: str) -> tuple[str, ...]:
    policy_name = _policy(table_name)
    policy_sql = (
        f"CREATE POLICY {policy_name} ON {table_name} "
        f"USING ({TENANT_SCOPE_SQL}) WITH CHECK ({TENANT_SCOPE_SQL})"
    )
    return (
        f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        policy_sql,
    )


def _disable_statements(table_name: str) -> tuple[str, str, str]:
    policy_name = _policy(table_name)
    return (
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY",
    )


def _emit(
    tables: Iterable[str],
    statement_builder: Callable[[str], tuple[str, ...]],
) -> None:
    for table_name in tables:
        for statement in statement_builder(table_name):
            op.execute(statement)


def upgrade() -> None:
    bind = _postgres()
    if bind is None:
        return

    present = _present_tables(bind)
    _emit(
        (table_name for table_name in PRODUCT_CATALOG_TABLES if table_name in present),
        _enable_statements,
    )


def downgrade() -> None:
    bind = _postgres()
    if bind is None:
        return

    present = _present_tables(bind)
    _emit(
        (
            table_name
            for table_name in reversed(PRODUCT_CATALOG_TABLES)
            if table_name in present
        ),
        _disable_statements,
    )
