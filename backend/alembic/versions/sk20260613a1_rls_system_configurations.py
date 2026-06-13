"""enable RLS on system configurations tenant table

Revision ID: sk20260613a1
Revises: sj20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sk20260613a1"
down_revision = "sj20260613a1"
branch_labels = None
depends_on = None


SYSTEM_CONFIGURATIONS_RLS_TABLES = ("configuracoes_sistema",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=SYSTEM_CONFIGURATIONS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=SYSTEM_CONFIGURATIONS_RLS_TABLES,
        enable=False,
    )
