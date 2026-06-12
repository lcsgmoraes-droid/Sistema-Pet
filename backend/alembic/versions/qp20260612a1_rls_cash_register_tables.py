"""enable RLS on cash register tenant tables

Revision ID: qp20260612a1
Revises: qo20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qp20260612a1"
down_revision = "qo20260612a1"
branch_labels = None
depends_on = None


CASH_REGISTER_RLS_TABLES = (
    "caixas",
    "movimentacoes_caixa",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CASH_REGISTER_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CASH_REGISTER_RLS_TABLES,
        enable=False,
    )
