"""enable RLS on stock location tenant tables

Revision ID: ss20260613a1
Revises: sr20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "ss20260613a1"
down_revision = "sr20260613a1"
branch_labels = None
depends_on = None


STOCK_LOCATIONS_RLS_TABLES = ("locais_estoque",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=STOCK_LOCATIONS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=STOCK_LOCATIONS_RLS_TABLES,
        enable=False,
    )
