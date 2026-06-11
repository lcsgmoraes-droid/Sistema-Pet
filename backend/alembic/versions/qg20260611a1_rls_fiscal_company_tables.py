"""enable RLS on fiscal company tenant tables

Revision ID: qg20260611a1
Revises: qf20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qg20260611a1"
down_revision = "qf20260611a1"
branch_labels = None
depends_on = None


FISCAL_COMPANY_RLS_TABLES = (
    "empresa_config_fiscal",
    "simples_nacional_mensal",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=FISCAL_COMPANY_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=FISCAL_COMPANY_RLS_TABLES,
        enable=False,
    )
