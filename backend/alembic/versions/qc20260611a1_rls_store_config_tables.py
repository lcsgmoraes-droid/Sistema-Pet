"""enable RLS on store configuration tenant tables

Revision ID: qc20260611a1
Revises: qb20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "qc20260611a1"
down_revision = "qb20260611a1"
branch_labels = None
depends_on = None


STORE_CONFIG_TABLES = ("empresa_config_geral", "configuracoes_custo_moto")
TENANT_POLICY = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"

UPGRADE_SQL = (
    "ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS {policy} ON {table}",
    "CREATE POLICY {policy} ON {table} USING ({guard}) WITH CHECK ({guard})",
)
DOWNGRADE_SQL = (
    "DROP POLICY IF EXISTS {policy} ON {table}",
    "ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY",
    "ALTER TABLE {table} DISABLE ROW LEVEL SECURITY",
)


def _run_policy_templates(sql_templates: tuple[str, ...], table_names: tuple[str, ...]) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    for table_name in table_names:
        if not inspector.has_table(table_name):
            continue

        values = {
            "table": table_name,
            "policy": f"{table_name}_tenant_isolation",
            "guard": TENANT_POLICY,
        }
        for template in sql_templates:
            op.execute(template.format(**values))


def upgrade() -> None:
    _run_policy_templates(UPGRADE_SQL, STORE_CONFIG_TABLES)


def downgrade() -> None:
    _run_policy_templates(DOWNGRADE_SQL, tuple(reversed(STORE_CONFIG_TABLES)))
