"""Add historico_conciliacao table

Revision ID: 20260212_add_historico_conciliacao
Revises: 20260211_add_conciliacao_3_abas
Create Date: 2026-02-12

Adiciona tabela de histórico de conciliações realizadas para:
- Registrar quais datas/operadoras já foram conciliadas
- Evitar reprocessamento duplicado
- Auditoria completa do processo
- Histórico consultável
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers
revision = '20260212_add_historico_conciliacao'
down_revision = '20260211_add_conciliacao_3_abas'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================
    # CRIAR TABELA HISTORICO_CONCILIACAO
    # ========================================
    op.create_table(
        'historico_conciliacao',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False, index=True),
        
        # Identificação única da conciliação
        sa.Column('data_referencia', sa.Date(), nullable=False, index=True, 
                  comment='Data conciliada (ex: 10/02/2026)'),
        sa.Column('operadora', sa.String(100), nullable=False, index=True, 
                  comment='Operadora: Stone, PagSeguro, Rede, Cielo, etc.'),
        
        # Status do processo
        sa.Column('status', sa.String(50), nullable=False, server_default='em_andamento',
                  comment='em_andamento | concluida | reprocessada | cancelada'),
        
        # Abas concluídas
        sa.Column('aba1_concluida', sa.Boolean(), nullable=False, server_default='false',
                  comment='Conciliação de Vendas'),
        sa.Column('aba2_concluida', sa.Boolean(), nullable=False, server_default='false',
                  comment='Validação de Recebimentos'),
        sa.Column('aba3_concluida', sa.Boolean(), nullable=False, server_default='false',
                  comment='Amarração Automática'),
        
        sa.Column('aba1_concluida_em', sa.DateTime(), nullable=True),
        sa.Column('aba2_concluida_em', sa.DateTime(), nullable=True),
        sa.Column('aba3_concluida_em', sa.DateTime(), nullable=True),
        
        # Metadados da conciliação
        sa.Column('arquivos_processados', JSONB, nullable=True,
                  comment='Lista de arquivos: [{nome, tipo, tamanho, hash}]'),
        sa.Column('totais', JSONB, nullable=True,
                  comment='Valores totais: {vendas, recebimentos, amarrado, divergencias}'),
        
        sa.Column('divergencias_encontradas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('divergencias_aceitas', sa.Boolean(), nullable=False, server_default='false'),
        
        # Resultado da amarração (Aba 3)
        sa.Column('parcelas_amarradas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parcelas_orfas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('taxa_amarracao', sa.Numeric(5, 2), nullable=True,
                  comment='% de sucesso da amarração'),
        
        # Auditoria
        sa.Column('usuario_responsavel', sa.String(200), nullable=True,
                  comment='Usuário que realizou'),
        sa.Column('observacoes', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('concluida_em', sa.DateTime(), nullable=True,
                  comment='Quando todas as 3 abas terminarem'),
        sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False, 
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Primary Key
        sa.PrimaryKeyConstraint('id'),
        
        # Índice composto para buscar rapidamente
        sa.Index('ix_historico_data_operadora', 'tenant_id', 'data_referencia', 'operadora'),
    )
    
    # Índices adicionais
    op.create_index('ix_historico_status', 'historico_conciliacao', ['status'])
    op.create_index('ix_historico_criado_em', 'historico_conciliacao', ['criado_em'])


def downgrade():
    # Remover tabela
    op.drop_index('ix_historico_criado_em', 'historico_conciliacao')
    op.drop_index('ix_historico_status', 'historico_conciliacao')
    op.drop_index('ix_historico_data_operadora', 'historico_conciliacao')
    op.drop_table('historico_conciliacao')
