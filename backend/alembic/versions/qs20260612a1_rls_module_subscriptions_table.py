"""enable RLS on module subscriptions tenant table

Revision ID: qs20260612a1
Revises: qr20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qs20260612a1"
down_revision = "qr20260612a1"
branch_labels = None
depends_on = None


MODULE_SUBSCRIPTIONS_RLS_TABLES = ("assinaturas_modulos",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=MODULE_SUBSCRIPTIONS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=MODULE_SUBSCRIPTIONS_RLS_TABLES,
        enable=False,
    )
