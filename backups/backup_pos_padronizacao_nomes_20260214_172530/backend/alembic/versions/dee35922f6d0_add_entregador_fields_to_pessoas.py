"""add entregador fields to pessoas

Revision ID: dee35922f6d0
Revises: 9cf2c5641d3d
Create Date: 2026-01-31 16:13:43.983230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dee35922f6d0'
down_revision: Union[str, Sequence[str], None] = '9cf2c5641d3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona campos de entregador na tabela clientes."""
    op.add_column('clientes', sa.Column('is_entregador', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('clientes', sa.Column('is_terceirizado', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('clientes', sa.Column('recebe_repasse', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('clientes', sa.Column('gera_conta_pagar', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column('clientes', sa.Column('tipo_vinculo_entrega', sa.String(length=20), nullable=True))
    op.add_column('clientes', sa.Column('valor_padrao_entrega', sa.Numeric(10, 2), nullable=True))
    op.add_column('clientes', sa.Column('valor_por_km', sa.Numeric(10, 2), nullable=True))
    op.add_column('clientes', sa.Column('recebe_comissao_entrega', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Remove campos de entregador da tabela clientes."""
    op.drop_column('clientes', 'recebe_comissao_entrega')
    op.drop_column('clientes', 'valor_por_km')
    op.drop_column('clientes', 'valor_padrao_entrega')
    op.drop_column('clientes', 'tipo_vinculo_entrega')

    op.drop_column('clientes', 'gera_conta_pagar')
    op.drop_column('clientes', 'recebe_repasse')
    op.drop_column('clientes', 'is_terceirizado')
    op.drop_column('clientes', 'is_entregador')

