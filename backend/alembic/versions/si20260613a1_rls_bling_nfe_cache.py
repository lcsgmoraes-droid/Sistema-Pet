"""enable RLS on Bling NFe cache

Revision ID: si20260613a1
Revises: sh20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "si20260613a1"
down_revision = "sh20260613a1"
branch_labels = None
depends_on = None


BLING_NFE_CACHE_RLS_TABLES = ("bling_notas_fiscais_cache",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BLING_NFE_CACHE_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=BLING_NFE_CACHE_RLS_TABLES,
        enable=False,
    )
