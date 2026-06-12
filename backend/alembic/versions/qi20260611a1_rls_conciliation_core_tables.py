"""enable RLS on conciliation core tenant tables

Revision ID: qi20260611a1
Revises: qh20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qi20260611a1"
down_revision = "qh20260611a1"
branch_labels = None
depends_on = None


CONCILIATION_CORE_RLS_TABLES = (
    "empresa_parametros",
    "arquivos_evidencia",
    "conciliacao_importacoes",
    "conciliacao_lotes",
    "conciliacao_recebimentos",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CONCILIATION_CORE_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CONCILIATION_CORE_RLS_TABLES,
        enable=False,
    )
