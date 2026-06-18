"""enable RLS on product tax configuration tenant tables

Revision ID: pw20260611a1
Revises: pv20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from collections.abc import Iterable

from alembic import op
import sqlalchemy as sa


revision = "pw20260611a1"
down_revision = "pv20260611a1"
branch_labels = None
depends_on = None


TAX_CONFIG_TABLES = (
    "produto_config_fiscal",
    "kit_config_fiscal",
    "variacao_config_fiscal",
)

TENANT_SCOPE = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def get_postgresql_bind():
    bind = op.get_bind()
    return bind if bind.dialect.name == "postgresql" else None


def existing_tax_config_tables(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return {table_name for table_name in TAX_CONFIG_TABLES if inspector.has_table(table_name)}


def _policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def _enable_rls_sql(table_name: str) -> tuple[str, ...]:
    policy_name = _policy_name(table_name)
    return (
        f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        (
            f"CREATE POLICY {policy_name} ON {table_name} "
            f"USING ({TENANT_SCOPE}) WITH CHECK ({TENANT_SCOPE})"
        ),
    )


def _disable_rls_sql(table_name: str) -> tuple[str, ...]:
    policy_name = _policy_name(table_name)
    return (
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY",
    )


def _execute_sql(sql_groups: Iterable[tuple[str, ...]]) -> None:
    for statements in sql_groups:
        for statement in statements:
            op.execute(statement)


def upgrade() -> None:
    bind = get_postgresql_bind()
    if bind is None:
        return

    present = existing_tax_config_tables(bind)
    _execute_sql(
        _enable_rls_sql(table_name)
        for table_name in TAX_CONFIG_TABLES
        if table_name in present
    )


def downgrade() -> None:
    bind = get_postgresql_bind()
    if bind is None:
        return

    present = existing_tax_config_tables(bind)
    _execute_sql(
        _disable_rls_sql(table_name)
        for table_name in reversed(TAX_CONFIG_TABLES)
        if table_name in present
    )
