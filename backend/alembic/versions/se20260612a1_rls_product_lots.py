"""enable RLS on product lots tenant table

Revision ID: se20260612a1
Revises: sd20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "se20260612a1"
down_revision = "sd20260612a1"
branch_labels = None
depends_on = None


PRODUCT_LOTS_RLS_TABLES = ("produto_lotes",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRODUCT_LOTS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRODUCT_LOTS_RLS_TABLES,
        enable=False,
    )
