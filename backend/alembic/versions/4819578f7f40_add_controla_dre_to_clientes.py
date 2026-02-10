"""add_controla_dre_to_clientes

Revision ID: 4819578f7f40
Revises: 8422585f3dec
Create Date: 2026-02-10 15:57:02.385833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4819578f7f40'
down_revision: Union[str, Sequence[str], None] = '8422585f3dec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Adiciona campo controla_dre na tabela clientes."""
    # Adicionar coluna controla_dre (default=True, todos os clientes/fornecedores controlam DRE por padrão)
    op.add_column('clientes', sa.Column('controla_dre', sa.Boolean(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema - Remove campo controla_dre."""
    op.drop_column('clientes', 'controla_dre')
