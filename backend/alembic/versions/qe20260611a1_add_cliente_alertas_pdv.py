"""add customer POS alerts

Revision ID: qe20260611a1
Revises: qc20260611a1
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "qe20260611a1"
down_revision = "qc20260611a1"
branch_labels = None
depends_on = None


def _clientes_table_exists() -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table("clientes")


def upgrade() -> None:
    if not _clientes_table_exists():
        return
    op.add_column("clientes", sa.Column("alertas_pdv", sa.JSON(), nullable=True))


def downgrade() -> None:
    if not _clientes_table_exists():
        return
    op.drop_column("clientes", "alertas_pdv")
