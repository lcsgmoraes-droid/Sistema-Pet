"""add_percentual_taxa_entrega

Revision ID: 08846c42f5cb
Revises: 48dad2e87a0d
Create Date: 2026-02-08 23:27:10.099882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08846c42f5cb'
down_revision: Union[str, Sequence[str], None] = '48dad2e87a0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campos de percentuais de taxa de entrega na tabela vendas
    op.add_column('vendas', sa.Column('percentual_taxa_entregador', sa.DECIMAL(5, 2), nullable=True, server_default='0'))
    op.add_column('vendas', sa.Column('percentual_taxa_loja', sa.DECIMAL(5, 2), nullable=True, server_default='100'))
    op.add_column('vendas', sa.Column('valor_taxa_entregador', sa.DECIMAL(10, 2), nullable=True, server_default='0'))
    op.add_column('vendas', sa.Column('valor_taxa_loja', sa.DECIMAL(10, 2), nullable=True, server_default='0'))
    
    # Adicionar campos de custo operacional na tabela users (entregadores)
    op.add_column('users', sa.Column('custo_operacional_tipo', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('custo_operacional_valor', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('users', sa.Column('custo_operacional_controla_rh_id', sa.String(100), nullable=True))
    
    # Atualizar vendas existentes: se tem taxa_entrega > 0, assumir 100% para loja
    op.execute("""
        UPDATE vendas 
        SET valor_taxa_loja = taxa_entrega,
            percentual_taxa_loja = 100,
            percentual_taxa_entregador = 0,
            valor_taxa_entregador = 0
        WHERE taxa_entrega > 0
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remover campos da tabela vendas
    op.drop_column('vendas', 'valor_taxa_loja')
    op.drop_column('vendas', 'valor_taxa_entregador')
    op.drop_column('vendas', 'percentual_taxa_loja')
    op.drop_column('vendas', 'percentual_taxa_entregador')
    
    # Remover campos da tabela users
    op.drop_column('users', 'custo_operacional_controla_rh_id')
    op.drop_column('users', 'custo_operacional_valor')
    op.drop_column('users', 'custo_operacional_tipo')
