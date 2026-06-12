"""enable RLS on financial foundation tenant tables

Revision ID: qm20260612a1
Revises: ql20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qm20260612a1"
down_revision = "ql20260612a1"
branch_labels = None
depends_on = None


FINANCIAL_FOUNDATION_RLS_TABLES = (
    "contas_bancarias",
    "categorias_financeiras",
    "tipo_despesas",
    "formas_pagamento_taxas",
    "configuracao_impostos",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=FINANCIAL_FOUNDATION_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=FINANCIAL_FOUNDATION_RLS_TABLES,
        enable=False,
    )
