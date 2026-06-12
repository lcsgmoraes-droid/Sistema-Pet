"""enable RLS on legacy bank reconciliation tenant tables

Revision ID: ql20260612a1
Revises: qk20260611a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "ql20260612a1"
down_revision = "qk20260611a1"
branch_labels = None
depends_on = None


LEGACY_BANK_RECONCILIATION_RLS_TABLES = (
    "extratos_bancarios",
    "movimentacoes_bancarias",
    "regras_conciliacao",
    "provisoes_automaticas",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=LEGACY_BANK_RECONCILIATION_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=LEGACY_BANK_RECONCILIATION_RLS_TABLES,
        enable=False,
    )
