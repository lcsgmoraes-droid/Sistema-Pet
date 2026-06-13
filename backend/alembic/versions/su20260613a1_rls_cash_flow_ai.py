"""enable RLS on cash flow AI tenant tables

Revision ID: su20260613a1
Revises: st20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "su20260613a1"
down_revision = "st20260613a1"
branch_labels = None
depends_on = None


CASH_FLOW_AI_RLS_TABLES = (
    "fluxo_caixa",
    "indices_saude_caixa",
    "projecao_fluxo_caixa",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CASH_FLOW_AI_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CASH_FLOW_AI_RLS_TABLES,
        enable=False,
    )
