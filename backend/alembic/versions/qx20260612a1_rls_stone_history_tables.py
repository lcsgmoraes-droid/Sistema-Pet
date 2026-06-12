"""enable RLS on Stone history tenant tables

Revision ID: qx20260612a1
Revises: qw20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qx20260612a1"
down_revision = "qw20260612a1"
branch_labels = None
depends_on = None


STONE_HISTORY_RLS_TABLES = (
    "stone_transactions",
    "stone_transaction_logs",
    "stone_configs",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=STONE_HISTORY_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=STONE_HISTORY_RLS_TABLES,
        enable=False,
    )
