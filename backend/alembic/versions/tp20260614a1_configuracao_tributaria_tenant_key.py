"""prepare configuracao_tributaria tenant key

Revision ID: tp20260614a1
Revises: to20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op


revision = "tp20260614a1"
down_revision = "to20260614a1"
branch_labels = None
depends_on = None


CONFIGURACAO_TRIBUTARIA_TABLE = "configuracao_tributaria"
LEGACY_USUARIO_UNIQUE = "configuracao_tributaria_usuario_id_key"
TENANT_UNIQUE = "uq_configuracao_tributaria_tenant_id"


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        return

    op.execute(
        f"ALTER TABLE {CONFIGURACAO_TRIBUTARIA_TABLE} "
        f"DROP CONSTRAINT IF EXISTS {LEGACY_USUARIO_UNIQUE}"
    )
    op.create_unique_constraint(
        TENANT_UNIQUE,
        CONFIGURACAO_TRIBUTARIA_TABLE,
        ["tenant_id"],
    )


def downgrade() -> None:
    if not _is_postgresql():
        return

    op.drop_constraint(
        TENANT_UNIQUE,
        CONFIGURACAO_TRIBUTARIA_TABLE,
        type_="unique",
    )
    op.create_unique_constraint(
        LEGACY_USUARIO_UNIQUE,
        CONFIGURACAO_TRIBUTARIA_TABLE,
        ["usuario_id"],
    )
