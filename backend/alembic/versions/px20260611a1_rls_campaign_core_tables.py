"""enable RLS on campaign core tenant tables

Revision ID: px20260611a1
Revises: pw20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from collections.abc import Iterable

from alembic import op
import sqlalchemy as sa


revision = "px20260611a1"
down_revision = "pw20260611a1"
branch_labels = None
depends_on = None


CAMPAIGN_CORE_TABLES = (
    "campaigns",
    "campaign_executions",
    "campaign_run_log",
    "campaign_locks",
)

TENANT_POLICY_SQL = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def postgresql_bind():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def existing_campaign_core_tables(bind) -> tuple[str, ...]:
    inspector = sa.inspect(bind)
    return tuple(
        table_name
        for table_name in CAMPAIGN_CORE_TABLES
        if inspector.has_table(table_name)
    )


def tenant_policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def enable_rls_statements(table_name: str) -> tuple[str, ...]:
    policy_name = tenant_policy_name(table_name)
    return (
        f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        (
            f"CREATE POLICY {policy_name} ON {table_name} "
            f"USING ({TENANT_POLICY_SQL}) WITH CHECK ({TENANT_POLICY_SQL})"
        ),
    )


def disable_rls_statements(table_name: str) -> tuple[str, ...]:
    policy_name = tenant_policy_name(table_name)
    return (
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY",
    )


def run_statements(statement_groups: Iterable[tuple[str, ...]]) -> None:
    for statements in statement_groups:
        for statement in statements:
            op.execute(statement)


def upgrade() -> None:
    bind = postgresql_bind()
    if bind is None:
        return

    existing_tables = existing_campaign_core_tables(bind)
    run_statements(
        enable_rls_statements(table_name)
        for table_name in CAMPAIGN_CORE_TABLES
        if table_name in existing_tables
    )


def downgrade() -> None:
    bind = postgresql_bind()
    if bind is None:
        return

    existing_tables = existing_campaign_core_tables(bind)
    run_statements(
        disable_rls_statements(table_name)
        for table_name in reversed(CAMPAIGN_CORE_TABLES)
        if table_name in existing_tables
    )
