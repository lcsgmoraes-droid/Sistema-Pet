"""add_timestamps_to_padroes_categorizacao_ia

Revision ID: 1b6d197509be
Revises: 908f232111a4
Create Date: 2026-01-27 14:34:56.650754

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b6d197509be'
down_revision: Union[str, Sequence[str], None] = '908f232111a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona created_at e updated_at à tabela padroes_categorizacao_ia"""
    
    # Adicionar created_at
    op.add_column('padroes_categorizacao_ia', sa.Column(
        'created_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    # Adicionar updated_at
    op.add_column('padroes_categorizacao_ia', sa.Column(
        'updated_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    print("✅ Timestamps adicionados a padroes_categorizacao_ia")


def downgrade() -> None:
    """Remove created_at e updated_at da tabela padroes_categorizacao_ia"""
    op.drop_column('padroes_categorizacao_ia', 'updated_at')
    op.drop_column('padroes_categorizacao_ia', 'created_at')
