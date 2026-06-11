"""enable RLS on campaign history tenant tables

Revision ID: qa20260611a1
Revises: pz20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "qa20260611a1"
down_revision = "pz20260611a1"
branch_labels = None
depends_on = None


HISTORY_TABLES = (
    "customer_rank_history",
    "notification_log",
    "customer_merge_logs",
)

TENANT_MATCH = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _postgresql_bind():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def _existing_history_tables(bind) -> tuple[str, ...]:
    inspector = sa.inspect(bind)
    return tuple(
        table_name for table_name in HISTORY_TABLES if inspector.has_table(table_name)
    )


def _policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def _enable_tenant_rls(table_name: str) -> None:
    policy_name = _policy_name(table_name)
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}")
    op.execute(
        f"CREATE POLICY {policy_name} ON {table_name} "
        f"USING ({TENANT_MATCH}) WITH CHECK ({TENANT_MATCH})"
    )


def _disable_tenant_rls(table_name: str) -> None:
    policy_name = _policy_name(table_name)
    op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}")
    op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    bind = _postgresql_bind()
    if bind is None:
        return

    existing_tables = _existing_history_tables(bind)
    for table_name in HISTORY_TABLES:
        if table_name in existing_tables:
            _enable_tenant_rls(table_name)


def downgrade() -> None:
    bind = _postgresql_bind()
    if bind is None:
        return

    existing_tables = _existing_history_tables(bind)
    for table_name in reversed(HISTORY_TABLES):
        if table_name in existing_tables:
            _disable_tenant_rls(table_name)
