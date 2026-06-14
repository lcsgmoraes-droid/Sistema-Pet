"""enable RLS on legacy DRE analysis tenant tables

Revision ID: tc20260614a1
Revises: tb20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "tc20260614a1"
down_revision = "tb20260614a1"
branch_labels = None
depends_on = None


DRE_LEGACY_RLS_TABLES = (
    "dre_produtos",
    "dre_categorias_analise",
    "dre_comparacoes",
    "dre_insights",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=DRE_LEGACY_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=DRE_LEGACY_RLS_TABLES,
        enable=False,
    )
