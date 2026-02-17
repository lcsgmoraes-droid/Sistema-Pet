"""add_dre_gerada_fields_to_vendas

Revision ID: bb1be66338a4
Revises: 8f6f56d8a345
Create Date: 2026-01-29 22:21:34.191781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb1be66338a4'
down_revision: Union[str, Sequence[str], None] = '8f6f56d8a345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adiciona coluna de controle para geração de DRE por competência
    op.add_column('vendas', sa.Column('dre_gerada', sa.Boolean(), nullable=False, server_default='false'))
    
    # Adiciona coluna de data de geração da DRE
    op.add_column('vendas', sa.Column('data_geracao_dre', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove colunas adicionadas
    op.drop_column('vendas', 'data_geracao_dre')
    op.drop_column('vendas', 'dre_gerada')
