"""enable RLS on banho tosa pacotes tenant tables

Revision ID: ry20260612a1
Revises: rx20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "ry20260612a1"
down_revision = "rx20260612a1"
branch_labels = None
depends_on = None


BANHO_TOSA_PACOTES_RLS_TABLES = (
    "banho_tosa_pacotes",
    "banho_tosa_pacote_creditos",
    "banho_tosa_pacote_movimentos",
    "banho_tosa_recorrencias",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BANHO_TOSA_PACOTES_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BANHO_TOSA_PACOTES_RLS_TABLES,
        enable=False,
    )
