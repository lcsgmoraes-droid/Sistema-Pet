"""enable RLS on banho tosa atendimento tenant tables

Revision ID: rv20260612a1
Revises: ru20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "rv20260612a1"
down_revision = "ru20260612a1"
branch_labels = None
depends_on = None


BANHO_TOSA_ATENDIMENTO_RLS_TABLES = (
    "banho_tosa_atendimentos",
    "banho_tosa_etapas",
    "banho_tosa_fotos",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BANHO_TOSA_ATENDIMENTO_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BANHO_TOSA_ATENDIMENTO_RLS_TABLES,
        enable=False,
    )
