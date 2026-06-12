"""enable RLS on acquirer template tenant table

Revision ID: qj20260611a1
Revises: qi20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qj20260611a1"
down_revision = "qi20260611a1"
branch_labels = None
depends_on = None


ACQUIRER_TEMPLATE_RLS_TABLES = ("adquirentes_templates",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=ACQUIRER_TEMPLATE_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=ACQUIRER_TEMPLATE_RLS_TABLES,
        enable=False,
    )
