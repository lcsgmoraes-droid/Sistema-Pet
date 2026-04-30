"""expandir campos de referencia das movimentacoes de estoque

Revision ID: ll20260430a1
Revises: kk20260430a3
Create Date: 2026-04-30 09:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "ll20260430a1"
down_revision = "kk20260430a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("estoque_movimentacoes"):
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns("estoque_movimentacoes")}

    if "motivo" in colunas:
        op.alter_column(
            "estoque_movimentacoes",
            "motivo",
            existing_type=sa.String(length=20),
            type_=sa.String(length=80),
            existing_nullable=True,
        )

    if "referencia_tipo" in colunas:
        op.alter_column(
            "estoque_movimentacoes",
            "referencia_tipo",
            existing_type=sa.String(length=20),
            type_=sa.String(length=50),
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("estoque_movimentacoes"):
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns("estoque_movimentacoes")}

    if "referencia_tipo" in colunas:
        op.alter_column(
            "estoque_movimentacoes",
            "referencia_tipo",
            existing_type=sa.String(length=50),
            type_=sa.String(length=20),
            existing_nullable=True,
        )

    if "motivo" in colunas:
        op.alter_column(
            "estoque_movimentacoes",
            "motivo",
            existing_type=sa.String(length=80),
            type_=sa.String(length=20),
            existing_nullable=True,
        )
