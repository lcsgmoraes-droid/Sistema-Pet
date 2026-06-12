"""enable RLS on legacy acquirer template tenant table

Revision ID: qk20260611a1
Revises: qj20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qk20260611a1"
down_revision = "qj20260611a1"
branch_labels = None
depends_on = None


LEGACY_ACQUIRER_TEMPLATE_RLS_TABLES = ("templates_adquirentes",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=LEGACY_ACQUIRER_TEMPLATE_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=LEGACY_ACQUIRER_TEMPLATE_RLS_TABLES,
        enable=False,
    )
