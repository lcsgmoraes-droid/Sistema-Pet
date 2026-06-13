"""enable RLS on app access profiles

Revision ID: sw20260613a1
Revises: sv20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sw20260613a1"
down_revision = "sv20260613a1"
branch_labels = None
depends_on = None


APP_ACCESS_PROFILES_RLS_TABLES = ("app_access_profiles",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=APP_ACCESS_PROFILES_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=APP_ACCESS_PROFILES_RLS_TABLES,
        enable=False,
    )
