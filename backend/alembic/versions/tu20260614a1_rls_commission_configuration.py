"""enable RLS on commission configuration

Revision ID: tu20260614a1
Revises: tt20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "tu20260614a1"
down_revision = "tt20260614a1"
branch_labels = None
depends_on = None


COMMISSION_CONFIGURATION_RLS_TABLES = ("comissoes_configuracao",)

TENANT_GUARD = TENANT_RLS_GUARD


def _has_commission_configuration_table() -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    return sa.inspect(bind).has_table("comissoes_configuracao")


def _prepare_commission_configuration_tenant_column() -> None:
    if not _has_commission_configuration_table():
        return

    op.execute(
        "ALTER TABLE comissoes_configuracao ADD COLUMN IF NOT EXISTS tenant_id uuid"
    )
    op.execute(
        """
        UPDATE comissoes_configuracao cc
        SET tenant_id = c.tenant_id
        FROM clientes c
        WHERE cc.funcionario_id = c.id
          AND cc.tenant_id IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_comissoes_configuracao_tenant_id
        ON comissoes_configuracao (tenant_id)
        """
    )


def upgrade() -> None:
    _prepare_commission_configuration_tenant_column()
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=COMMISSION_CONFIGURATION_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=COMMISSION_CONFIGURATION_RLS_TABLES,
        enable=False,
    )
