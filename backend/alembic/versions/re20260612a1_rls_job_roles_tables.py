"""enable RLS on job role tenant tables

Revision ID: re20260612a1
Revises: rd20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "re20260612a1"
down_revision = "rd20260612a1"
branch_labels = None
depends_on = None


JOB_ROLES_RLS_TABLES = ("cargos",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=JOB_ROLES_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=JOB_ROLES_RLS_TABLES,
        enable=False,
    )
