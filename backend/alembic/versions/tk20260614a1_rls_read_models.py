"""enable RLS on read models

Revision ID: tk20260614a1
Revises: tj20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "tk20260614a1"
down_revision = "tj20260614a1"
branch_labels = None
depends_on = None


READ_MODEL_RLS_TABLES = (
    "read_vendas_resumo_diario",
    "read_performance_parceiro",
    "read_receita_mensal",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=READ_MODEL_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=READ_MODEL_RLS_TABLES,
        enable=False,
    )
