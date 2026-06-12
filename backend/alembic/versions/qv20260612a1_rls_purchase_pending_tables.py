"""enable RLS on purchase pending tenant tables

Revision ID: qv20260612a1
Revises: qu20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qv20260612a1"
down_revision = "qu20260612a1"
branch_labels = None
depends_on = None


PURCHASE_PENDING_RLS_TABLES = (
    "compras_pendencias_fornecedor",
    "compras_pendencias_fornecedor_itens",
    "compras_pendencias_fornecedor_historico",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PURCHASE_PENDING_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=PURCHASE_PENDING_RLS_TABLES,
        enable=False,
    )
