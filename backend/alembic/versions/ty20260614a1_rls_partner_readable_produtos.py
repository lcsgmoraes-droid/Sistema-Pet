"""enable partner-readable RLS on produtos

Revision ID: ty20260614a1
Revises: tx20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import (
    PARTNER_LINK_EXISTS_GUARD,
    PARTNER_OWN_TENANT_GUARD,
    PARTNER_SELECT_GUARD,
    PARTNER_TENANT_SETTING_UUID,
    apply_partner_readable_rls,
)


revision = "ty20260614a1"
down_revision = "tx20260614a1"
branch_labels = None
depends_on = None


PARTNER_READABLE_PRODUCT_RLS_TABLES = ("produtos",)
TENANT_SETTING_UUID = PARTNER_TENANT_SETTING_UUID
OWN_TENANT_GUARD = PARTNER_OWN_TENANT_GUARD
LINK_EXISTS_GUARD = PARTNER_LINK_EXISTS_GUARD
SELECT_GUARD = PARTNER_SELECT_GUARD


def upgrade() -> None:
    apply_partner_readable_rls(
        op_module=op,
        sa_module=sa,
        table_names=PARTNER_READABLE_PRODUCT_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_partner_readable_rls(
        op_module=op,
        sa_module=sa,
        table_names=PARTNER_READABLE_PRODUCT_RLS_TABLES,
        enable=False,
    )
