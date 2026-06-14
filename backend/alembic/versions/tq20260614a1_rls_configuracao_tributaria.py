"""enable RLS on configuracao_tributaria

Revision ID: tq20260614a1
Revises: tp20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "tq20260614a1"
down_revision = "tp20260614a1"
branch_labels = None
depends_on = None


CONFIGURACAO_TRIBUTARIA_RLS_TABLES = ("configuracao_tributaria",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CONFIGURACAO_TRIBUTARIA_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=CONFIGURACAO_TRIBUTARIA_RLS_TABLES,
        enable=False,
    )
