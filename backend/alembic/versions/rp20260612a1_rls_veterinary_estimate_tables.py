"""enable RLS on veterinary estimate tenant tables

Revision ID: rp20260612a1
Revises: ro20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "rp20260612a1"
down_revision = "ro20260612a1"
branch_labels = None
depends_on = None


VETERINARY_ESTIMATE_RLS_TABLES = (
    "vet_orcamentos",
    "vet_orcamento_itens",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=VETERINARY_ESTIMATE_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=VETERINARY_ESTIMATE_RLS_TABLES,
        enable=False,
    )
