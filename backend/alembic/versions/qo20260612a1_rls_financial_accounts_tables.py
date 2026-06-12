"""enable RLS on financial accounts tenant tables

Revision ID: qo20260612a1
Revises: qn20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qo20260612a1"
down_revision = "qn20260612a1"
branch_labels = None
depends_on = None


FINANCIAL_ACCOUNTS_RLS_TABLES = (
    "contas_pagar",
    "contas_receber",
    "pagamentos",
    "recebimentos",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=FINANCIAL_ACCOUNTS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=FINANCIAL_ACCOUNTS_RLS_TABLES,
        enable=False,
    )
