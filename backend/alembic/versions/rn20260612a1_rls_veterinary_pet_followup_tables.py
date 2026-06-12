"""enable RLS on veterinary pet follow-up tenant tables

Revision ID: rn20260612a1
Revises: rm20260612a1
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "rn20260612a1"
down_revision = "rm20260612a1"
branch_labels = None
depends_on = None


VETERINARY_PET_FOLLOWUP_RLS_TABLES = (
    "vet_peso_registros",
    "vet_fotos_clinicas",
    "vet_perfil_comportamental",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=VETERINARY_PET_FOLLOWUP_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=VETERINARY_PET_FOLLOWUP_RLS_TABLES,
        enable=False,
    )
