"""enable RLS on conciliation audit tenant tables

Revision ID: qh20260611a1
Revises: qg20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qh20260611a1"
down_revision = "qg20260611a1"
branch_labels = None
depends_on = None


CONCILIATION_AUDIT_RLS_TABLES = (
    "conciliacao_validacoes",
    "conciliacao_logs",
    "conciliacao_metricas",
    "historico_conciliacao",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CONCILIATION_AUDIT_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CONCILIATION_AUDIT_RLS_TABLES,
        enable=False,
    )
