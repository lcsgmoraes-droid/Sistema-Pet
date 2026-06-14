"""enable RLS on sale settlements

Revision ID: te20260614a1
Revises: td20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "te20260614a1"
down_revision = "td20260614a1"
branch_labels = None
depends_on = None


SALE_SETTLEMENT_RLS_TABLES = ("venda_baixas",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=SALE_SETTLEMENT_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=SALE_SETTLEMENT_RLS_TABLES,
        enable=False,
    )
