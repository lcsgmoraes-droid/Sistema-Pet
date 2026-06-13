"""enable RLS on inbound invoice tenant tables

Revision ID: so20260613a1
Revises: sn20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "so20260613a1"
down_revision = "sn20260613a1"
branch_labels = None
depends_on = None


NOTAS_ENTRADA_RLS_TABLES = ("notas_entrada", "notas_entrada_itens")

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=NOTAS_ENTRADA_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=NOTAS_ENTRADA_RLS_TABLES,
        enable=False,
    )
