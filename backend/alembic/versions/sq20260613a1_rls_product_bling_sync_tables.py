"""enable RLS on product Bling sync tenant tables

Revision ID: sq20260613a1
Revises: sp20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sq20260613a1"
down_revision = "sp20260613a1"
branch_labels = None
depends_on = None


PRODUCT_BLING_SYNC_RLS_TABLES = ("produto_bling_sync", "produto_bling_sync_queue")

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRODUCT_BLING_SYNC_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRODUCT_BLING_SYNC_RLS_TABLES,
        enable=False,
    )
