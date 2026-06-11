"""enable RLS on campaign drawing tenant tables

Revision ID: pz20260611a1
Revises: py20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "pz20260611a1"
down_revision = "py20260611a1"
branch_labels = None
depends_on = None


DRAWING_TABLES = (
    "drawings",
    "drawing_entries",
)

TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _postgresql_bind():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def _existing_drawing_tables(bind) -> frozenset[str]:
    inspector = sa.inspect(bind)
    return frozenset(
        table_name for table_name in DRAWING_TABLES if inspector.has_table(table_name)
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
        f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
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

    existing_tables = _existing_drawing_tables(bind)
    for table_name in DRAWING_TABLES:
        if table_name in existing_tables:
            _enable_rls(table_name)


def downgrade() -> None:
    bind = _postgresql_bind()
    if bind is None:
        return

    existing_tables = _existing_drawing_tables(bind)
    for table_name in reversed(DRAWING_TABLES):
        if table_name in existing_tables:
            _disable_rls(table_name)
