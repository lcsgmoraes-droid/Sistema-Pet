"""enable RLS on product catalog relation tables

Revision ID: sy20260614a1
Revises: sx20260613a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sy20260614a1"
down_revision = "sx20260613a1"
branch_labels = None
depends_on = None


PRODUCT_CATALOG_RELATION_RLS_TABLES = (
    "produto_imagens",
    "produto_kit_componentes",
    "produto_granel_vinculos",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRODUCT_CATALOG_RELATION_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PRODUCT_CATALOG_RELATION_RLS_TABLES,
        enable=False,
    )
