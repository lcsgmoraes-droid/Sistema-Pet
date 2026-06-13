"""enable RLS on product variation attribute tables

Revision ID: sh20260613a1
Revises: sg20260612a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sh20260613a1"
down_revision = "sg20260612a1"
branch_labels = None
depends_on = None


PRODUCT_VARIATION_ATTRIBUTES_RLS_TABLES = (
    "produtos_atributos",
    "produtos_atributos_opcoes",
    "produtos_variacoes_atributos",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRODUCT_VARIATION_ATTRIBUTES_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRODUCT_VARIATION_ATTRIBUTES_RLS_TABLES,
        enable=False,
    )
