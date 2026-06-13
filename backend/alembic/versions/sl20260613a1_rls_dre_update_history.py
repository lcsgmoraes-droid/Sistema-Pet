"""enable RLS on DRE update history tenant table

Revision ID: sl20260613a1
Revises: sk20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sl20260613a1"
down_revision = "sk20260613a1"
branch_labels = None
depends_on = None


DRE_UPDATE_HISTORY_RLS_TABLES = ("historico_atualizacao_dre",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=DRE_UPDATE_HISTORY_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=DRE_UPDATE_HISTORY_RLS_TABLES,
        enable=False,
    )
