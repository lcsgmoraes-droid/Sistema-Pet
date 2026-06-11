"""enable RLS on core onboarding tenant tables

Revision ID: ps20260611a1
Revises: pr20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "ps20260611a1"
down_revision = "pr20260611a1"
branch_labels = None
depends_on = None


CORE_ONBOARDING_TABLES = (
    "formas_pagamento",
    "especies",
    "racas",
)

RLS_TENANT_PREDICATE = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def _bind():
    return op.get_bind()


def _inspector():
    return sa.inspect(_bind())


def _table_exists(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def _is_postgresql() -> bool:
    bind = _bind()
    return bind.dialect.name == "postgresql"


def _enable_rls(table_name: str) -> None:
    if not _table_exists(table_name):
        return

    policy_name = _policy_name(table_name)
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}")
    op.execute(
        f"""
        CREATE POLICY {policy_name}
        ON {table_name}
        USING ({RLS_TENANT_PREDICATE})
        WITH CHECK ({RLS_TENANT_PREDICATE})
        """
    )


def _disable_rls(table_name: str) -> None:
    if not _table_exists(table_name):
        return

    policy_name = _policy_name(table_name)
    op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}")
    op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    if not _is_postgresql():
        return

    for table_name in CORE_ONBOARDING_TABLES:
        _enable_rls(table_name)


def downgrade() -> None:
    if not _is_postgresql():
        return

    for table_name in reversed(CORE_ONBOARDING_TABLES):
        _disable_rls(table_name)
