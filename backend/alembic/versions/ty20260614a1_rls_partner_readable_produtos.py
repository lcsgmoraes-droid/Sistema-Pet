"""enable partner-readable RLS on produtos

Revision ID: ty20260614a1
Revises: tx20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "ty20260614a1"
down_revision = "tx20260614a1"
branch_labels = None
depends_on = None


PARTNER_READABLE_PRODUCT_RLS_TABLES = ("produtos",)
TENANT_SETTING_UUID = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
OWN_TENANT_GUARD = f"tenant_id = {TENANT_SETTING_UUID}"
PARTNER_LINK_EXISTS_GUARD = (
    "EXISTS (SELECT 1 FROM vet_partner_link vpl "
    "WHERE vpl.empresa_tenant_id = tenant_id "
    f"AND vpl.vet_tenant_id = {TENANT_SETTING_UUID} "
    "AND vpl.ativo = true)"
)
PARTNER_SELECT_GUARD = f"({OWN_TENANT_GUARD}) OR ({PARTNER_LINK_EXISTS_GUARD})"


def _postgres_bind():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def _present_tables() -> list[str]:
    bind = _postgres_bind()
    if bind is None:
        return []

    inspector = sa.inspect(bind)
    return [
        table_name
        for table_name in PARTNER_READABLE_PRODUCT_RLS_TABLES
        if inspector.has_table(table_name)
    ]


def _policy_names(table_name: str) -> tuple[str, ...]:
    return (
        f"{table_name}_partner_select",
        f"{table_name}_tenant_insert",
        f"{table_name}_tenant_update",
        f"{table_name}_tenant_delete",
    )


def _drop_custom_policies(table_name: str, *, reverse: bool = False) -> None:
    policy_names = _policy_names(table_name)
    if reverse:
        policy_names = tuple(reversed(policy_names))

    for policy_name in policy_names:
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}")


def _enable_partner_readable_rls(table_name: str) -> None:
    select_policy, insert_policy, update_policy, delete_policy = _policy_names(table_name)

    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}")
    _drop_custom_policies(table_name)

    op.execute(
        f"CREATE POLICY {select_policy} ON {table_name} "
        f"FOR SELECT USING ({PARTNER_SELECT_GUARD})"
    )
    op.execute(
        f"CREATE POLICY {insert_policy} ON {table_name} "
        f"FOR INSERT WITH CHECK ({OWN_TENANT_GUARD})"
    )
    op.execute(
        f"CREATE POLICY {update_policy} ON {table_name} "
        f"FOR UPDATE USING ({OWN_TENANT_GUARD}) WITH CHECK ({OWN_TENANT_GUARD})"
    )
    op.execute(
        f"CREATE POLICY {delete_policy} ON {table_name} "
        f"FOR DELETE USING ({OWN_TENANT_GUARD})"
    )


def _disable_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    for table_name in _present_tables():
        _enable_partner_readable_rls(table_name)


def downgrade() -> None:
    for table_name in reversed(_present_tables()):
        _drop_custom_policies(table_name, reverse=True)
        _disable_rls(table_name)
