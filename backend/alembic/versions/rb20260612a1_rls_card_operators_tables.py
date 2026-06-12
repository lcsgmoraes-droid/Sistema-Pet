"""enable RLS on card operator tenant tables

Revision ID: rb20260612a1
Revises: ra20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "rb20260612a1"
down_revision = "ra20260612a1"
branch_labels = None
depends_on = None


CARD_OPERATORS_RLS_TABLES = ("operadoras_cartao",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CARD_OPERATORS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CARD_OPERATORS_RLS_TABLES,
        enable=False,
    )
