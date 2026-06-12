"""enable RLS on delivery route tenant tables

Revision ID: sb20260612a1
Revises: sa20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sb20260612a1"
down_revision = "sa20260612a1"
branch_labels = None
depends_on = None


ROTAS_ENTREGA_RLS_TABLES = (
    "rotas_entrega",
    "rotas_entrega_paradas",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=ROTAS_ENTREGA_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=ROTAS_ENTREGA_RLS_TABLES,
        enable=False,
    )
