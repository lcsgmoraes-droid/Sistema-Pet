"""add venda retirada fields

Revision ID: om20260515a4
Revises: ol20260515a3
Create Date: 2026-05-15 16:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "om20260515a4"
down_revision = "ol20260515a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("vendas"):
        return

    columns = {column["name"] for column in inspector.get_columns("vendas")}
    if "tipo_retirada" not in columns:
        op.add_column("vendas", sa.Column("tipo_retirada", sa.String(length=20), nullable=True))
    if "palavra_chave_retirada" not in columns:
        op.add_column("vendas", sa.Column("palavra_chave_retirada", sa.String(length=100), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("vendas"):
        return

    columns = {column["name"] for column in inspector.get_columns("vendas")}
    if "palavra_chave_retirada" in columns:
        op.drop_column("vendas", "palavra_chave_retirada")
    if "tipo_retirada" in columns:
        op.drop_column("vendas", "tipo_retirada")
