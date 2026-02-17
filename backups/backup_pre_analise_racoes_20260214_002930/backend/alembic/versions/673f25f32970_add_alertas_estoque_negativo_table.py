"""add_alertas_estoque_negativo_table

Revision ID: 673f25f32970
Revises: 0e9ee2b0cca2
Create Date: 2026-02-12 21:46:31.191999

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '673f25f32970'
down_revision: Union[str, Sequence[str], None] = '0e9ee2b0cca2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Criar tabela de alertas de estoque negativo (MODELO CONTROLADO)
    op.create_table(
        'alertas_estoque_negativo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('produto_id', sa.Integer(), nullable=False),
        sa.Column('produto_nome', sa.String(length=255), nullable=False),
        sa.Column('estoque_anterior', sa.Float(), nullable=False),
        sa.Column('quantidade_vendida', sa.Float(), nullable=False),
        sa.Column('estoque_resultante', sa.Float(), nullable=False),
        sa.Column('venda_id', sa.Integer(), nullable=True),
        sa.Column('venda_codigo', sa.String(length=50), nullable=True),
        sa.Column('data_alerta', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pendente'),
        sa.Column('data_resolucao', sa.DateTime(), nullable=True),
        sa.Column('usuario_resolucao_id', sa.Integer(), nullable=True),
        sa.Column('observacao', sa.String(length=500), nullable=True),
        sa.Column('notificado', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('critico', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['venda_id'], ['vendas.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['usuario_resolucao_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Índices para performance
    op.create_index('idx_alertas_estoque_tenant_status', 'alertas_estoque_negativo', ['tenant_id', 'status'])
    op.create_index('idx_alertas_estoque_produto', 'alertas_estoque_negativo', ['produto_id'])
    op.create_index('idx_alertas_estoque_critico', 'alertas_estoque_negativo', ['critico'])
    op.create_index('idx_alertas_estoque_data', 'alertas_estoque_negativo', ['data_alerta'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remover índices
    op.drop_index('idx_alertas_estoque_data', table_name='alertas_estoque_negativo')
    op.drop_index('idx_alertas_estoque_critico', table_name='alertas_estoque_negativo')
    op.drop_index('idx_alertas_estoque_produto', table_name='alertas_estoque_negativo')
    op.drop_index('idx_alertas_estoque_tenant_status', table_name='alertas_estoque_negativo')
    
    # Remover tabela
    op.drop_table('alertas_estoque_negativo')
