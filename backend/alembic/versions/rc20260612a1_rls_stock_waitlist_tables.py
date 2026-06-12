"""enable RLS on stock waitlist tenant tables

Revision ID: rc20260612a1
Revises: rb20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "rc20260612a1"
down_revision = "rb20260612a1"
branch_labels = None
depends_on = None


STOCK_WAITLIST_RLS_TABLES = ("pendencias_estoque",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=STOCK_WAITLIST_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=STOCK_WAITLIST_RLS_TABLES,
        enable=False,
    )
