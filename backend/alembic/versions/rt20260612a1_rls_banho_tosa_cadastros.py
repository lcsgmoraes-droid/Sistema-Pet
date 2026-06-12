"""enable RLS on banho tosa cadastro tenant tables

Revision ID: rt20260612a1
Revises: rs20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "rt20260612a1"
down_revision = "rs20260612a1"
branch_labels = None
depends_on = None


BANHO_TOSA_CADASTRO_RLS_TABLES = (
    "banho_tosa_recursos",
    "banho_tosa_servicos",
    "banho_tosa_precos_servico",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BANHO_TOSA_CADASTRO_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BANHO_TOSA_CADASTRO_RLS_TABLES,
        enable=False,
    )
