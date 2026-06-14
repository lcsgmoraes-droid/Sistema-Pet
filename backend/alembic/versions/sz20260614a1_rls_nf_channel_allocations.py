"""enable RLS on fiscal note channel allocation tables

Revision ID: sz20260614a1
Revises: sy20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sz20260614a1"
down_revision = "sy20260614a1"
branch_labels = None
depends_on = None


NF_CHANNEL_ALLOCATION_RLS_TABLES = (
    "nota_fiscal_rateio_canal",
    "nota_fiscal_item_rateio_canal",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=NF_CHANNEL_ALLOCATION_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=NF_CHANNEL_ALLOCATION_RLS_TABLES,
        enable=False,
    )
