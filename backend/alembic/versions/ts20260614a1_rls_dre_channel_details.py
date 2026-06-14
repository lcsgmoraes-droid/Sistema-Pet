"""enable RLS on dre_detalhe_canais

Revision ID: ts20260614a1
Revises: tr20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "ts20260614a1"
down_revision = "tr20260614a1"
branch_labels = None
depends_on = None


DRE_CHANNEL_DETAIL_RLS_TABLES = ("dre_detalhe_canais",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=DRE_CHANNEL_DETAIL_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=DRE_CHANNEL_DETAIL_RLS_TABLES,
        enable=False,
    )
