"""enable RLS on ration option tenant tables

Revision ID: pu20260611a1
Revises: pt20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from collections.abc import Iterable

from alembic import op
import sqlalchemy as sa


revision = "pu20260611a1"
down_revision = "pt20260611a1"
branch_labels = None
depends_on = None


RATION_OPTION_TABLES = (
    "linhas_racao",
    "portes_animal",
    "fases_publico",
    "tipos_tratamento",
    "sabores_proteina",
    "apresentacoes_peso",
)

TENANT_GUARD_SQL = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def _postgres_bind():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def _existing_option_tables(bind) -> frozenset[str]:
    inspector = sa.inspect(bind)
    return frozenset(
        table_name
        for table_name in RATION_OPTION_TABLES
        if inspector.has_table(table_name)
    )


def _policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def _create_policy_sql(table_name: str) -> str:
    policy_name = _policy_name(table_name)
    return (
        f"CREATE POLICY {policy_name} ON {table_name} "
        f"USING ({TENANT_GUARD_SQL}) WITH CHECK ({TENANT_GUARD_SQL})"
    )


def _upgrade_sql_for(table_name: str) -> tuple[str, ...]:
    policy_name = _policy_name(table_name)
    return (
        f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        _create_policy_sql(table_name),
    )


def _downgrade_sql_for(table_name: str) -> tuple[str, ...]:
    policy_name = _policy_name(table_name)
    return (
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY",
    )


def _run_sql(statements_by_table: Iterable[tuple[str, ...]]) -> None:
    for table_statements in statements_by_table:
        for statement in table_statements:
            op.execute(statement)


def upgrade() -> None:
    bind = _postgres_bind()
    if bind is None:
        return

    existing_tables = _existing_option_tables(bind)
    _run_sql(
        _upgrade_sql_for(table_name)
        for table_name in RATION_OPTION_TABLES
        if table_name in existing_tables
    )


def downgrade() -> None:
    bind = _postgres_bind()
    if bind is None:
        return

    existing_tables = _existing_option_tables(bind)
    _run_sql(
        _downgrade_sql_for(table_name)
        for table_name in reversed(RATION_OPTION_TABLES)
        if table_name in existing_tables
    )
