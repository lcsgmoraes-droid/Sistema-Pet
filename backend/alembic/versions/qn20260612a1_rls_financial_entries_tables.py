"""enable RLS on financial entries tenant tables

Revision ID: qn20260612a1
Revises: qm20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qn20260612a1"
down_revision = "qm20260612a1"
branch_labels = None
depends_on = None


FINANCIAL_ENTRIES_RLS_TABLES = (
    "movimentacoes_financeiras",
    "lancamentos_manuais",
    "lancamentos_recorrentes",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=FINANCIAL_ENTRIES_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=FINANCIAL_ENTRIES_RLS_TABLES,
        enable=False,
    )
