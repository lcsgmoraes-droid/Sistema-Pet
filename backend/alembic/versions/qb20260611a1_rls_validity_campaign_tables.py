"""enable RLS on validity campaign tenant tables

Revision ID: qb20260611a1
Revises: qa20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "qb20260611a1"
down_revision = "qa20260611a1"
branch_labels = None
depends_on = None


VALIDITY_CAMPAIGN_TABLES = (
    "campanha_validade_automatica",
    "campanha_validade_exclusoes",
)

TENANT_POLICY = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _postgresql_bind():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def _existing_validity_campaign_tables(bind) -> tuple[str, ...]:
    inspector = sa.inspect(bind)
    return tuple(
        table_name
        for table_name in VALIDITY_CAMPAIGN_TABLES
        if inspector.has_table(table_name)
    )


def _policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def _enable_rls(table_name: str) -> None:
    policy_name = _policy_name(table_name)
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}")
    op.execute(
        f"CREATE POLICY {policy_name} ON {table_name} "
        f"USING ({TENANT_POLICY}) WITH CHECK ({TENANT_POLICY})"
    )


def _disable_rls(table_name: str) -> None:
    policy_name = _policy_name(table_name)
    op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}")
    op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    bind = _postgresql_bind()
    if bind is None:
        return

    existing_tables = _existing_validity_campaign_tables(bind)
    for table_name in VALIDITY_CAMPAIGN_TABLES:
        if table_name in existing_tables:
            _enable_rls(table_name)


def downgrade() -> None:
    bind = _postgresql_bind()
    if bind is None:
        return

    existing_tables = _existing_validity_campaign_tables(bind)
    for table_name in reversed(VALIDITY_CAMPAIGN_TABLES):
        if table_name in existing_tables:
            _disable_rls(table_name)
