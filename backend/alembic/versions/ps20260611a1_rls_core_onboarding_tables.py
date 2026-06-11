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


def _policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def _postgresql_bind():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def _existing_targets(bind) -> list[str]:
    inspector = sa.inspect(bind)
    return [
        table_name
        for table_name in CORE_ONBOARDING_TABLES
        if inspector.has_table(table_name)
    ]


def _upgrade_commands(table_name: str) -> tuple[str, ...]:
    policy_name = _policy_name(table_name)
    return (
        f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        f"""
        CREATE POLICY {policy_name}
        ON {table_name}
        USING ({RLS_TENANT_PREDICATE})
        WITH CHECK ({RLS_TENANT_PREDICATE})
        """,
    )


def _downgrade_commands(table_name: str) -> tuple[str, str, str]:
    policy_name = _policy_name(table_name)
    return (
        f"DROP POLICY IF EXISTS {policy_name} ON {table_name}",
        f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY",
    )


def _execute(commands: tuple[str, ...]) -> None:
    for sql in commands:
        op.execute(sql)


def upgrade() -> None:
    bind = _postgresql_bind()
    if bind is None:
        return

    for table_name in _existing_targets(bind):
        _execute(_upgrade_commands(table_name))


def downgrade() -> None:
    bind = _postgresql_bind()
    if bind is None:
        return

    for table_name in reversed(_existing_targets(bind)):
        _execute(_downgrade_commands(table_name))
