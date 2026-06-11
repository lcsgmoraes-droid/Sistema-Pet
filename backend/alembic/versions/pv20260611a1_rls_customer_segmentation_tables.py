"""enable RLS on customer segmentation tenant tables

Revision ID: pv20260611a1
Revises: pu20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "pv20260611a1"
down_revision = "pu20260611a1"
branch_labels = None
depends_on = None


SEGMENTATION_TABLE = "cliente_segmentos"
TENANT_POLICY_NAME = f"{SEGMENTATION_TABLE}_tenant_isolation"
TENANT_MATCH_SQL = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def postgresql_connection():
    bind = op.get_bind()
    return bind if bind.dialect.name == "postgresql" else None


def table_exists(bind, table_name: str) -> bool:
    return bool(sa.inspect(bind).has_table(table_name))


def _segmentation_upgrade_commands() -> list[str]:
    return [
        f"ALTER TABLE {SEGMENTATION_TABLE} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {SEGMENTATION_TABLE} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {TENANT_POLICY_NAME} ON {SEGMENTATION_TABLE}",
        (
            f"CREATE POLICY {TENANT_POLICY_NAME} ON {SEGMENTATION_TABLE} "
            f"USING ({TENANT_MATCH_SQL}) WITH CHECK ({TENANT_MATCH_SQL})"
        ),
    ]


def _segmentation_downgrade_commands() -> list[str]:
    return [
        f"DROP POLICY IF EXISTS {TENANT_POLICY_NAME} ON {SEGMENTATION_TABLE}",
        f"ALTER TABLE {SEGMENTATION_TABLE} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {SEGMENTATION_TABLE} DISABLE ROW LEVEL SECURITY",
    ]


def _execute_when_table_exists(bind, commands: list[str]) -> None:
    if not table_exists(bind, SEGMENTATION_TABLE):
        return

    for command in commands:
        op.execute(command)


def upgrade() -> None:
    bind = postgresql_connection()
    if bind is not None:
        _execute_when_table_exists(bind, _segmentation_upgrade_commands())


def downgrade() -> None:
    bind = postgresql_connection()
    if bind is not None:
        _execute_when_table_exists(bind, _segmentation_downgrade_commands())
