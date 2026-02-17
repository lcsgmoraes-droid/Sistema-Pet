"""add_product_variations_fields

Revision ID: 307b83c509eb
Revises: 3e9f678b9c43
Create Date: 2026-01-27 02:30:03.893657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '307b83c509eb'
down_revision: Union[str, Sequence[str], None] = '3e9f678b9c43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add variation_attributes and variation_signature to produtos."""
    # Adicionar campos para suporte a variações
    op.add_column('produtos', sa.Column('variation_attributes', sa.JSON(), nullable=True))
    op.add_column('produtos', sa.Column('variation_signature', sa.String(length=255), nullable=True))
    
    # Criar índice composto para garantir unicidade de variação por tenant
    op.create_index(
        'idx_produtos_variation_signature',
        'produtos',
        ['tenant_id', 'variation_signature'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remover índice
    op.drop_index('idx_produtos_variation_signature', table_name='produtos')
    
    # Remover colunas
    op.drop_column('produtos', 'variation_signature')
    op.drop_column('produtos', 'variation_attributes')
