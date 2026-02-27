"""add_retirado_por_to_vendas

Adiciona coluna retirado_por na tabela vendas (para registrar
nome de quem retirou o pedido no e-commerce).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-27 10:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona coluna retirado_por em vendas."""
    op.add_column('vendas', sa.Column('retirado_por', sa.String(150), nullable=True))


def downgrade() -> None:
    """Remove coluna retirado_por de vendas."""
    op.drop_column('vendas', 'retirado_por')
