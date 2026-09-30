"""Permite CPF do consumidor na NFC-e sem cadastro de cliente.

Revision ID: zzz20260930a1
Revises: zzy20260921a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zzz20260930a1"
down_revision = "zzy20260921a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendas", sa.Column("nfe_consumidor_cpf", sa.String(11), nullable=True))


def downgrade() -> None:
    op.drop_column("vendas", "nfe_consumidor_cpf")
