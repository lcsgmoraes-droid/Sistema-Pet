"""enable RLS on DRE chart tenant tables

Revision ID: qt20260612a1
Revises: qs20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qt20260612a1"
down_revision = "qs20260612a1"
branch_labels = None
depends_on = None


DRE_CHART_RLS_TABLES = (
    "dre_categorias",
    "dre_subcategorias",
    "regras_classificacao_dre",
    "historico_classificacao_dre",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=DRE_CHART_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=DRE_CHART_RLS_TABLES,
        enable=False,
    )
