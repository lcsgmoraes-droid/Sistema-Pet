"""enable RLS on RBAC tenant tables

Revision ID: rf20260612a1
Revises: re20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "rf20260612a1"
down_revision = "re20260612a1"
branch_labels = None
depends_on = None


RBAC_RLS_TABLES = ("roles", "role_permissions")

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=RBAC_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=RBAC_RLS_TABLES,
        enable=False,
    )
