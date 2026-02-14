"""add_produto_opcoes_racao_fields

Revision ID: 86967908c0e9
Revises: 20260212_fix_historico_timestamps
Create Date: 2026-02-14 04:59:20.393686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86967908c0e9'
down_revision: Union[str, Sequence[str], None] = '20260212_fix_historico_timestamps'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona campos de opções de ração à tabela produtos."""
    
    # Adicionar colunas de foreign key para as opções de ração
    op.add_column('produtos', sa.Column('linha_racao_id', sa.Integer(), nullable=True))
    op.add_column('produtos', sa.Column('porte_animal_id', sa.Integer(), nullable=True))
    op.add_column('produtos', sa.Column('fase_publico_id', sa.Integer(), nullable=True))
    op.add_column('produtos', sa.Column('tipo_tratamento_id', sa.Integer(), nullable=True))
    op.add_column('produtos', sa.Column('sabor_proteina_id', sa.Integer(), nullable=True))
    op.add_column('produtos', sa.Column('apresentacao_peso_id', sa.Integer(), nullable=True))
    
    # Criar foreign keys
    op.create_foreign_key(
        'fk_produtos_linha_racao',
        'produtos', 'linhas_racao',
        ['linha_racao_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_produtos_porte_animal',
        'produtos', 'portes_animal',
        ['porte_animal_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_produtos_fase_publico',
        'produtos', 'fases_publico',
        ['fase_publico_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_produtos_tipo_tratamento',
        'produtos', 'tipos_tratamento',
        ['tipo_tratamento_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_produtos_sabor_proteina',
        'produtos', 'sabores_proteina',
        ['sabor_proteina_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_produtos_apresentacao_peso',
        'produtos', 'apresentacoes_peso',
        ['apresentacao_peso_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Criar índices para melhor performance em queries
    op.create_index('ix_produtos_linha_racao_id', 'produtos', ['linha_racao_id'])
    op.create_index('ix_produtos_porte_animal_id', 'produtos', ['porte_animal_id'])
    op.create_index('ix_produtos_fase_publico_id', 'produtos', ['fase_publico_id'])
    op.create_index('ix_produtos_sabor_proteina_id', 'produtos', ['sabor_proteina_id'])


def downgrade() -> None:
    """Remove campos de opções de ração da tabela produtos."""
    
    # Remover índices
    op.drop_index('ix_produtos_sabor_proteina_id', table_name='produtos')
    op.drop_index('ix_produtos_fase_publico_id', table_name='produtos')
    op.drop_index('ix_produtos_porte_animal_id', table_name='produtos')
    op.drop_index('ix_produtos_linha_racao_id', table_name='produtos')
    
    # Remover foreign keys
    op.drop_constraint('fk_produtos_apresentacao_peso', 'produtos', type_='foreignkey')
    op.drop_constraint('fk_produtos_sabor_proteina', 'produtos', type_='foreignkey')
    op.drop_constraint('fk_produtos_tipo_tratamento', 'produtos', type_='foreignkey')
    op.drop_constraint('fk_produtos_fase_publico', 'produtos', type_='foreignkey')
    op.drop_constraint('fk_produtos_porte_animal', 'produtos', type_='foreignkey')
    op.drop_constraint('fk_produtos_linha_racao', 'produtos', type_='foreignkey')
    
    # Remover colunas
    op.drop_column('produtos', 'apresentacao_peso_id')
    op.drop_column('produtos', 'sabor_proteina_id')
    op.drop_column('produtos', 'tipo_tratamento_id')
    op.drop_column('produtos', 'fase_publico_id')
    op.drop_column('produtos', 'porte_animal_id')
    op.drop_column('produtos', 'linha_racao_id')
