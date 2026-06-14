"""enable RLS on extrato importacao tables

Revision ID: to20260614a1
Revises: tn20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "to20260614a1"
down_revision = "tn20260614a1"
branch_labels = None
depends_on = None


EXTRATO_IMPORTACAO_RLS_TABLES = (
    "arquivos_extrato_importados",
    "lancamentos_importados",
    "padroes_categorizacao_ia",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=EXTRATO_IMPORTACAO_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=EXTRATO_IMPORTACAO_RLS_TABLES,
        enable=False,
    )
