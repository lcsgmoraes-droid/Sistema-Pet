"""enable RLS on channel discounts

Revision ID: sx20260613a1
Revises: sw20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sx20260613a1"
down_revision = "sw20260613a1"
branch_labels = None
depends_on = None


CANAL_DESCONTOS_RLS_TABLES = ("canal_descontos",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CANAL_DESCONTOS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CANAL_DESCONTOS_RLS_TABLES,
        enable=False,
    )
