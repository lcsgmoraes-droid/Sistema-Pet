"""enable RLS on purchase order tenant tables

Revision ID: sn20260613a1
Revises: sm20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sn20260613a1"
down_revision = "sm20260613a1"
branch_labels = None
depends_on = None


PURCHASE_ORDER_RLS_TABLES = ("pedidos_compra", "pedidos_compra_itens")

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PURCHASE_ORDER_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PURCHASE_ORDER_RLS_TABLES,
        enable=False,
    )
