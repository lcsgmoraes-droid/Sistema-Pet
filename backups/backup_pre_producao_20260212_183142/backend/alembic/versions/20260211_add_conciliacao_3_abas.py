"""Add conciliação 3 abas (vendas, recebimentos, amarração)

Revision ID: 20260211_add_conciliacao_3_abas
Revises: 
Create Date: 2026-02-11

Adiciona estrutura completa para nova arquitetura de conciliação:
- Aba 1: Conciliação de Vendas (PDV vs Stone)
- Aba 2: Conciliação de Recebimentos (validação cascata)
- Aba 3: Amarração automática (baixa de parcelas)

Models:
- vendas: +conciliado_vendas, +conciliado_vendas_em
- contas_receber: +tipo_recebimento, +conciliacao_recebimento_id
- conciliacao_recebimentos: nova tabela
- conciliacao_metricas: nova tabela (KPIs de saúde)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = '20260211_add_conciliacao_3_abas'
down_revision = None  # Será preenchido automaticamente
branch_labels = None
depends_on = None


def upgrade():
    # ========================================
    # 1. ADICIONAR CAMPOS EM VENDAS (Aba 1)
    # ========================================
    op.add_column('vendas',
        sa.Column('conciliado_vendas', sa.Boolean(), nullable=False, server_default='false', comment='Se venda foi conferida na Aba 1 (PDV vs Stone)')
    )
    op.add_column('vendas',
        sa.Column('conciliado_vendas_em', sa.DateTime(), nullable=True, comment='Data/hora que vendas foram conferidas')
    )
    
    # Índice para performance
    op.create_index('ix_vendas_conciliado_vendas', 'vendas', ['conciliado_vendas'])
    
    # ========================================
    # 2. CRIAR TABELA CONCILIACAO_RECEBIMENTOS (Aba 2)
    # ========================================
    op.create_table(
        'conciliacao_recebimentos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        
        # Dados da planilha Stone
        sa.Column('nsu', sa.String(100), nullable=False, comment='NSU da transação'),
        sa.Column('data_recebimento', sa.Date(), nullable=False, comment='Data que dinheiro entrou'),
        sa.Column('valor', sa.Numeric(15, 2), nullable=False, comment='Valor do recebimento'),
        sa.Column('parcela_numero', sa.Integer(), nullable=True, comment='Número da parcela (1, 2, 3, etc)'),
        sa.Column('total_parcelas', sa.Integer(), nullable=True, comment='Total de parcelas da venda'),
        
        # Tipo de recebimento
        sa.Column('tipo_recebimento', sa.String(30), nullable=False, server_default='parcela_individual', 
                  comment='antecipacao (todas de vez) | parcela_individual (1/3, 2/3, etc)'),
        
        # Lote (agrupamento Stone)
        sa.Column('lote_id', sa.String(100), nullable=True, comment='ID do lote Stone'),
        sa.Column('lote_valor', sa.Numeric(15, 2), nullable=True, comment='Valor total do lote'),
        
        # Validação (Aba 2)
        sa.Column('validado', sa.Boolean(), nullable=False, server_default='false', comment='Se passou validação cascata (Aba 2)'),
        sa.Column('validado_em', sa.DateTime(), nullable=True, comment='Quando foi validado'),
        sa.Column('validacao_id', sa.Integer(), nullable=True, comment='FK para validação'),
        
        # Amarração (Aba 3)
        sa.Column('amarrado', sa.Boolean(), nullable=False, server_default='false', comment='Se foi amarrado a uma venda (Aba 3)'),
        sa.Column('amarrado_em', sa.DateTime(), nullable=True, comment='Quando foi amarrado'),
        sa.Column('venda_id', sa.Integer(), nullable=True, comment='FK para venda vinculada'),
        
        # Auditoria
        sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        
        # Constraints
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar FKs separadamente após tabela criada
    op.create_foreign_key(
        'fk_conciliacao_recebimentos_tenant',
        'conciliacao_recebimentos', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_conciliacao_recebimentos_venda',
        'conciliacao_recebimentos', 'vendas',
        ['venda_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Índices para performance
    op.create_index('ix_conciliacao_recebimentos_tenant_id', 'conciliacao_recebimentos', ['tenant_id'])
    op.create_index('ix_conciliacao_recebimentos_nsu', 'conciliacao_recebimentos', ['nsu'])
    op.create_index('ix_conciliacao_recebimentos_data', 'conciliacao_recebimentos', ['data_recebimento'])
    op.create_index('ix_conciliacao_recebimentos_lote', 'conciliacao_recebimentos', ['lote_id'])
    op.create_index('ix_conciliacao_recebimentos_validado', 'conciliacao_recebimentos', ['validado'])
    op.create_index('ix_conciliacao_recebimentos_amarrado', 'conciliacao_recebimentos', ['amarrado'])
    op.create_index('ix_conciliacao_recebimentos_venda', 'conciliacao_recebimentos', ['venda_id'])
    
    # ========================================
    # 3. ADICIONAR CAMPOS EM CONTAS_RECEBER (Aba 3)
    # ========================================
    op.add_column('contas_receber',
        sa.Column('tipo_recebimento', sa.String(30), nullable=True, 
                  comment='antecipacao (todas parcelas) | parcela_individual (1/3, 2/3, etc)')
    )
    op.add_column('contas_receber',
        sa.Column('conciliacao_recebimento_id', sa.Integer(), nullable=True, 
                  comment='FK para recebimento Stone (idempotência)')
    )
    
    # FK e índice
    op.create_foreign_key(
        'fk_contas_receber_conciliacao_recebimento',
        'contas_receber', 'conciliacao_recebimentos',
        ['conciliacao_recebimento_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_contas_receber_conciliacao_recebimento', 'contas_receber', ['conciliacao_recebimento_id'])
    
    # ========================================
    # 4. CRIAR TABELA CONCILIACAO_METRICAS (KPIs)
    # ========================================
    op.create_table(
        'conciliacao_metricas',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        
        # Data da métrica
        sa.Column('data_referencia', sa.Date(), nullable=False, comment='Data dos recebimentos processados'),
        
        # Quantidades
        sa.Column('total_recebimentos', sa.Integer(), nullable=False, server_default='0', 
                  comment='Total de recebimentos validados (Aba 2)'),
        sa.Column('recebimentos_amarrados', sa.Integer(), nullable=False, server_default='0', 
                  comment='Recebimentos amarrados automaticamente'),
        sa.Column('recebimentos_orfaos', sa.Integer(), nullable=False, server_default='0', 
                  comment='Recebimentos SEM venda correspondente'),
        
        # Valores
        sa.Column('valor_total_recebimentos', sa.Numeric(15, 2), nullable=False, server_default='0', 
                  comment='Valor total dos recebimentos'),
        sa.Column('valor_amarrado', sa.Numeric(15, 2), nullable=False, server_default='0', 
                  comment='Valor amarrado automaticamente'),
        sa.Column('valor_orfao', sa.Numeric(15, 2), nullable=False, server_default='0', 
                  comment='Valor órfão (sem venda)'),
        
        # KPI principal
        sa.Column('taxa_amarracao_automatica', sa.Numeric(5, 2), nullable=False, server_default='0', 
                  comment='% de amarração automática (98% = saudável, < 90% = CRÍTICO)'),
        
        # Alertas
        sa.Column('alerta_saude', sa.String(20), nullable=False, server_default='OK', 
                  comment='OK (>= 90%) | CRÍTICO (< 90%)'),
        
        # Parcelas liquidadas (transparência)
        sa.Column('parcelas_liquidadas', sa.Integer(), nullable=False, server_default='0', 
                  comment='Quantas parcelas foram baixadas'),
        sa.Column('valor_total_liquidado', sa.Numeric(15, 2), nullable=False, server_default='0', 
                  comment='Valor total liquidado'),
        
        # Auditoria
        sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('criado_por_id', sa.Integer(), nullable=False, comment='Quem processou Aba 3'),
        
        # Constraints
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar FKs separadamente após tabela criada
    op.create_foreign_key(
        'fk_conciliacao_metricas_tenant',
        'conciliacao_metricas', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_conciliacao_metricas_criado_por',
        'conciliacao_metricas', 'users',
        ['criado_por_id'], ['id'],
        ondelete='RESTRICT'
    )
    
    # Índices para performance e análises
    op.create_index('ix_conciliacao_metricas_tenant_id', 'conciliacao_metricas', ['tenant_id'])
    op.create_index('ix_conciliacao_metricas_data', 'conciliacao_metricas', ['data_referencia'])
    op.create_index('ix_conciliacao_metricas_taxa', 'conciliacao_metricas', ['taxa_amarracao_automatica'])
    op.create_index('ix_conciliacao_metricas_alerta', 'conciliacao_metricas', ['alerta_saude'])
    
    # Índice composto para consultas por tenant + data
    op.create_index('ix_conciliacao_metricas_tenant_data', 'conciliacao_metricas', ['tenant_id', 'data_referencia'])


def downgrade():
    # Reverter na ordem inversa
    
    # 4. Drop tabela conciliacao_metricas
    op.drop_index('ix_conciliacao_metricas_tenant_data', 'conciliacao_metricas')
    op.drop_index('ix_conciliacao_metricas_alerta', 'conciliacao_metricas')
    op.drop_index('ix_conciliacao_metricas_taxa', 'conciliacao_metricas')
    op.drop_index('ix_conciliacao_metricas_data', 'conciliacao_metricas')
    op.drop_index('ix_conciliacao_metricas_tenant_id', 'conciliacao_metricas')
    op.drop_table('conciliacao_metricas')
    
    # 3. Remover campos de contas_receber
    op.drop_index('ix_contas_receber_conciliacao_recebimento', 'contas_receber')
    op.drop_constraint('fk_contas_receber_conciliacao_recebimento', 'contas_receber', type_='foreignkey')
    op.drop_column('contas_receber', 'conciliacao_recebimento_id')
    op.drop_column('contas_receber', 'tipo_recebimento')
    
    # 2. Drop tabela conciliacao_recebimentos
    op.drop_index('ix_conciliacao_recebimentos_venda', 'conciliacao_recebimentos')
    op.drop_index('ix_conciliacao_recebimentos_amarrado', 'conciliacao_recebimentos')
    op.drop_index('ix_conciliacao_recebimentos_validado', 'conciliacao_recebimentos')
    op.drop_index('ix_conciliacao_recebimentos_lote', 'conciliacao_recebimentos')
    op.drop_index('ix_conciliacao_recebimentos_data', 'conciliacao_recebimentos')
    op.drop_index('ix_conciliacao_recebimentos_nsu', 'conciliacao_recebimentos')
    op.drop_index('ix_conciliacao_recebimentos_tenant_id', 'conciliacao_recebimentos')
    op.drop_table('conciliacao_recebimentos')
    
    # 1. Remover campos de vendas
    op.drop_index('ix_vendas_conciliado_vendas', 'vendas')
    op.drop_column('vendas', 'conciliado_vendas_em')
    op.drop_column('vendas', 'conciliado_vendas')
