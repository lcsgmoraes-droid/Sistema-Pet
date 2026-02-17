"""criar_tabela_rotas_entrega_paradas

Revision ID: 20260201_rotas_paradas
Revises: 
Create Date: 2026-02-01

ETAPA 9.3 - Rota Ótima (Sequência)
Cria tabela para armazenar paradas ordenadas de cada rota,
com a sequência otimizada pelo Google Directions API.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260201_rotas_paradas'
down_revision = '921c0845a97a'  # create_configuracoes_entrega
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Criar tabela rotas_entrega_paradas
    op.create_table(
        'rotas_entrega_paradas',
        sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rota_id', sa.Integer(), nullable=False),
        sa.Column('venda_id', sa.Integer(), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('endereco', sa.Text(), nullable=False),
        sa.Column('distancia_acumulada', sa.Numeric(10, 2), nullable=True),
        sa.Column('tempo_acumulado', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['rota_id'], ['rotas_entrega.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['venda_id'], ['vendas.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar índices
    op.create_index('ix_rotas_entrega_paradas_rota_id', 'rotas_entrega_paradas', ['rota_id'])
    op.create_index('ix_rotas_entrega_paradas_venda_id', 'rotas_entrega_paradas', ['venda_id'])
    op.create_index('ix_rotas_entrega_paradas_tenant_id', 'rotas_entrega_paradas', ['tenant_id'])
    
    # Índice composto para ordenação
    op.create_index(
        'ix_rotas_entrega_paradas_rota_ordem',
        'rotas_entrega_paradas',
        ['rota_id', 'ordem']
    )


def downgrade() -> None:
    op.drop_index('ix_rotas_entrega_paradas_rota_ordem', table_name='rotas_entrega_paradas')
    op.drop_index('ix_rotas_entrega_paradas_tenant_id', table_name='rotas_entrega_paradas')
    op.drop_index('ix_rotas_entrega_paradas_venda_id', table_name='rotas_entrega_paradas')
    op.drop_index('ix_rotas_entrega_paradas_rota_id', table_name='rotas_entrega_paradas')
    op.drop_table('rotas_entrega_paradas')
