"""enable RLS on price list tenant tables

Revision ID: sc20260612a1
Revises: sb20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sc20260612a1"
down_revision = "sb20260612a1"
branch_labels = None
depends_on = None


PRICE_LISTS_RLS_TABLES = (
    "listas_preco",
    "produto_listas_preco",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRICE_LISTS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRICE_LISTS_RLS_TABLES,
        enable=False,
    )
