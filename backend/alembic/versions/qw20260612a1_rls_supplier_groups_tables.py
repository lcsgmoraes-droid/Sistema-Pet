"""enable RLS on supplier group tenant tables

Revision ID: qw20260612a1
Revises: qv20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qw20260612a1"
down_revision = "qv20260612a1"
branch_labels = None
depends_on = None


SUPPLIER_GROUPS_RLS_TABLES = ("fornecedor_grupos",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=SUPPLIER_GROUPS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=SUPPLIER_GROUPS_RLS_TABLES,
        enable=False,
    )
