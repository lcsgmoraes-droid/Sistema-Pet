"""add_timestamps_arquivos_extrato

Revision ID: 5f3d34ae34b7
Revises: b8a7669f8249
Create Date: 2026-01-27 14:40:39.808409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f3d34ae34b7'
down_revision: Union[str, Sequence[str], None] = 'b8a7669f8249'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona created_at e updated_at à tabela arquivos_extrato_importados"""
    
    # Verificar se as colunas já existem
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('arquivos_extrato_importados')]
    
    if 'created_at' not in columns:
        op.add_column('arquivos_extrato_importados', sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()')
        ))
    
    if 'updated_at' not in columns:
        op.add_column('arquivos_extrato_importados', sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()')
        ))
    
    print("✅ Timestamps adicionados a arquivos_extrato_importados")


def downgrade() -> None:
    """Remove created_at e updated_at da tabela arquivos_extrato_importados"""
    op.drop_column('arquivos_extrato_importados', 'updated_at')
    op.drop_column('arquivos_extrato_importados', 'created_at')
