"""enable RLS on delivery configuration tenant table

Revision ID: qd20260611a1
Revises: qe20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "qd20260611a1"
down_revision = "qe20260611a1"
branch_labels = None
depends_on = None


TABLE_NAME = "configuracoes_entrega"
POLICY_NAME = f"{TABLE_NAME}_tenant_isolation"
TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _should_skip() -> bool:
    bind = op.get_bind()
    return bind.dialect.name != "postgresql" or not sa.inspect(bind).has_table(
        TABLE_NAME
    )


def _execute_all(statements: list[str]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    if _should_skip():
        return

    _execute_all(
        [
            f"ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY",
            f"ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY",
            f"DROP POLICY IF EXISTS {POLICY_NAME} ON {TABLE_NAME}",
            (
                f"CREATE POLICY {POLICY_NAME} ON {TABLE_NAME} "
                f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
            ),
        ]
    )


def downgrade() -> None:
    if _should_skip():
        return

    _execute_all(
        [
            f"DROP POLICY IF EXISTS {POLICY_NAME} ON {TABLE_NAME}",
            f"ALTER TABLE {TABLE_NAME} NO FORCE ROW LEVEL SECURITY",
            f"ALTER TABLE {TABLE_NAME} DISABLE ROW LEVEL SECURITY",
        ]
    )
