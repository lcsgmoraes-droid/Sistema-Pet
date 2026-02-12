"""add_unique_constraint_variation_signature

Revision ID: 1a1f49b0ebae
Revises: 307b83c509eb
Create Date: 2026-01-27 02:53:21.336030

Sprint 2 - Fechamento: Garantir integridade de variações
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a1f49b0ebae'
down_revision: Union[str, Sequence[str], None] = '307b83c509eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adiciona constraint UNIQUE para garantir que:
    - Não existam duas variações com mesma signature
    - Para o mesmo produto pai
    - No mesmo tenant
    
    Constraint: uq_produtos_variation_signature
    Colunas: (tenant_id, produto_pai_id, variation_signature)
    """
    
    # Criar constraint único para variações
    op.create_unique_constraint(
        'uq_produtos_variation_signature',
        'produtos',
        ['tenant_id', 'produto_pai_id', 'variation_signature']
    )


def downgrade() -> None:
    """Remove o constraint único de variações."""
    
    # Remover constraint
    op.drop_constraint(
        'uq_produtos_variation_signature',
        'produtos',
        type_='unique'
    )
