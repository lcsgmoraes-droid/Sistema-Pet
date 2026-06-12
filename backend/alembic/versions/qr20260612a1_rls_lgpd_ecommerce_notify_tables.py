"""enable RLS on LGPD and ecommerce notify tenant tables

Revision ID: qr20260612a1
Revises: qq20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "qr20260612a1"
down_revision = "qq20260612a1"
branch_labels = None
depends_on = None


LGPD_ECOMMERCE_NOTIFY_RLS_TABLES = (
    "data_subject_requests",
    "ecommerce_notify_requests",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=LGPD_ECOMMERCE_NOTIFY_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=LGPD_ECOMMERCE_NOTIFY_RLS_TABLES,
        enable=False,
    )
