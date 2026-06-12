"""enable RLS on veterinary partner link table

Revision ID: rq20260612a1
Revises: rp20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "rq20260612a1"
down_revision = "rp20260612a1"
branch_labels = None
depends_on = None


VET_PARTNER_LINK_RLS_TABLE = "vet_partner_link"
TENANT_SETTING_UUID = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
SELECT_GUARD = (
    f"empresa_tenant_id = {TENANT_SETTING_UUID} "
    f"OR vet_tenant_id = {TENANT_SETTING_UUID}"
)
WRITE_GUARD = f"empresa_tenant_id = {TENANT_SETTING_UUID}"

POLICY_NAMES = (
    "vet_partner_link_partner_select",
    "vet_partner_link_empresa_insert",
    "vet_partner_link_empresa_update",
    "vet_partner_link_empresa_delete",
)


def _is_postgresql_table_present() -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    return sa.inspect(bind).has_table(VET_PARTNER_LINK_RLS_TABLE)


def _drop_policies(policy_names: tuple[str, ...] = POLICY_NAMES) -> None:
    for policy_name in policy_names:
        op.execute(
            f"DROP POLICY IF EXISTS {policy_name} ON {VET_PARTNER_LINK_RLS_TABLE}"
        )


def upgrade() -> None:
    if not _is_postgresql_table_present():
        return

    op.execute(f"ALTER TABLE {VET_PARTNER_LINK_RLS_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {VET_PARTNER_LINK_RLS_TABLE} FORCE ROW LEVEL SECURITY")
    _drop_policies()

    op.execute(
        f"CREATE POLICY vet_partner_link_partner_select ON {VET_PARTNER_LINK_RLS_TABLE} "
        f"FOR SELECT USING ({SELECT_GUARD})"
    )
    op.execute(
        f"CREATE POLICY vet_partner_link_empresa_insert ON {VET_PARTNER_LINK_RLS_TABLE} "
        f"FOR INSERT WITH CHECK ({WRITE_GUARD})"
    )
    op.execute(
        f"CREATE POLICY vet_partner_link_empresa_update ON {VET_PARTNER_LINK_RLS_TABLE} "
        f"FOR UPDATE USING ({WRITE_GUARD}) WITH CHECK ({WRITE_GUARD})"
    )
    op.execute(
        f"CREATE POLICY vet_partner_link_empresa_delete ON {VET_PARTNER_LINK_RLS_TABLE} "
        f"FOR DELETE USING ({WRITE_GUARD})"
    )


def downgrade() -> None:
    if not _is_postgresql_table_present():
        return

    _drop_policies(tuple(reversed(POLICY_NAMES)))
    op.execute(f"ALTER TABLE {VET_PARTNER_LINK_RLS_TABLE} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {VET_PARTNER_LINK_RLS_TABLE} DISABLE ROW LEVEL SECURITY")
