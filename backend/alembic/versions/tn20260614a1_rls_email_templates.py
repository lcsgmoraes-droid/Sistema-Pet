"""enable RLS on emails_templates

Revision ID: tn20260614a1
Revises: tm20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "tn20260614a1"
down_revision = "tm20260614a1"
branch_labels = None
depends_on = None


EMAIL_TEMPLATES_RLS_TABLES = ("emails_templates",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=EMAIL_TEMPLATES_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=EMAIL_TEMPLATES_RLS_TABLES,
        enable=False,
    )
