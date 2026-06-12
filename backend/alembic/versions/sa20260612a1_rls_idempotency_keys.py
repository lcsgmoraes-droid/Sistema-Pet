"""enable RLS on idempotency keys tenant table

Revision ID: sa20260612a1
Revises: rz20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "sa20260612a1"
down_revision = "rz20260612a1"
branch_labels = None
depends_on = None


IDEMPOTENCY_KEYS_RLS_TABLES = ("idempotency_keys",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=IDEMPOTENCY_KEYS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=IDEMPOTENCY_KEYS_RLS_TABLES,
        enable=False,
    )
