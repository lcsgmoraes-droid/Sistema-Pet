"""enable RLS on negative stock alert tenant tables

Revision ID: rd20260612a1
Revises: rc20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "rd20260612a1"
down_revision = "rc20260612a1"
branch_labels = None
depends_on = None


NEGATIVE_STOCK_ALERTS_RLS_TABLES = ("alertas_estoque_negativo",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=NEGATIVE_STOCK_ALERTS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=NEGATIVE_STOCK_ALERTS_RLS_TABLES,
        enable=False,
    )
