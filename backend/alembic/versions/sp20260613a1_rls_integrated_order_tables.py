"""enable RLS on integrated order tenant tables

Revision ID: sp20260613a1
Revises: so20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sp20260613a1"
down_revision = "so20260613a1"
branch_labels = None
depends_on = None


INTEGRATED_ORDER_RLS_TABLES = ("pedidos_integrados", "pedidos_integrados_itens")

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=INTEGRATED_ORDER_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=INTEGRATED_ORDER_RLS_TABLES,
        enable=False,
    )
