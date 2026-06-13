"""enable RLS on bulk conversion tenant table

Revision ID: sg20260612a1
Revises: sf20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sg20260612a1"
down_revision = "sf20260612a1"
branch_labels = None
depends_on = None


BULK_CONVERSIONS_RLS_TABLES = ("granel_conversoes",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BULK_CONVERSIONS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BULK_CONVERSIONS_RLS_TABLES,
        enable=False,
    )
