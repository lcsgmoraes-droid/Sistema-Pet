"""Guarda instrução de pagamento da entrega sem registrar recebimento.

Revision ID: zzzc20261002a1
Revises: zzzb20261002a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzc20261002a1"
down_revision = "zzzb20261002a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendas", sa.Column("pagamento_entrega_previsto", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("vendas", "pagamento_entrega_previsto")
