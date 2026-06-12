"""enable RLS on veterinary schedule tenant tables

Revision ID: rl20260612a1
Revises: rk20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "rl20260612a1"
down_revision = "rk20260612a1"
branch_labels = None
depends_on = None


VETERINARY_SCHEDULE_RLS_TABLES = (
    "vet_agendamentos",
    "vet_consultas",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=VETERINARY_SCHEDULE_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=VETERINARY_SCHEDULE_RLS_TABLES,
        enable=False,
    )
