"""add_conciliacao_bancaria_tables

Revision ID: 9e78a5374aca
Revises: d157d64dac01
Create Date: 2026-02-11 00:17:59.550924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e78a5374aca'
down_revision: Union[str, Sequence[str], None] = 'd157d64dac01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Adiciona tabelas de conciliação bancária."""
    
    # Tabela: extratos_bancarios
    op.create_table(
        'extratos_bancarios',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('conta_bancaria_id', sa.Integer(), nullable=False),
        sa.Column('arquivo_nome', sa.String(255), nullable=True),
        sa.Column('data_upload', sa.DateTime(), nullable=True),
        sa.Column('periodo_inicio', sa.Date(), nullable=True),
        sa.Column('periodo_fim', sa.Date(), nullable=True),
        sa.Column('total_movimentacoes', sa.Integer(), nullable=True),
        sa.Column('conciliadas', sa.Integer(), default=0),
        sa.Column('pendentes', sa.Integer(), default=0),
        sa.Column('status', sa.String(50), nullable=True),  # 'processando', 'concluido', 'revisao'
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conta_bancaria_id'], ['contas_bancarias.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_extratos_tenant', 'extratos_bancarios', ['tenant_id'])
    op.create_index('ix_extratos_conta', 'extratos_bancarios', ['conta_bancaria_id'])
    op.create_index('ix_extratos_status', 'extratos_bancarios', ['status'])
    
    # Tabela: movimentacoes_bancarias
    op.create_table(
        'movimentacoes_bancarias',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('extrato_id', sa.UUID(), nullable=True),
        sa.Column('conta_bancaria_id', sa.Integer(), nullable=False),
        
        # Dados do OFX
        sa.Column('fitid', sa.String(255), nullable=True),  # ID único do banco
        sa.Column('data_movimento', sa.DateTime(), nullable=True),
        sa.Column('valor', sa.Numeric(15, 2), nullable=True),
        sa.Column('tipo', sa.String(20), nullable=True),  # 'CREDIT', 'DEBIT'
        sa.Column('memo', sa.Text(), nullable=True),  # Descrição original
        
        # Classificação
        sa.Column('status_conciliacao', sa.String(50), nullable=True),  # 'pendente', 'sugerido', 'conciliado', 'manual'
        sa.Column('confianca_sugestao', sa.Integer(), nullable=True),  # 0-100%
        
        # Vínculos
        sa.Column('tipo_vinculo', sa.String(50), nullable=True),  # 'fornecedor', 'transferencia', 'taxa', 'recebimento'
        sa.Column('fornecedor_id', sa.Integer(), nullable=True),
        sa.Column('conta_pagar_id', sa.Integer(), nullable=True),
        sa.Column('conta_receber_id', sa.Integer(), nullable=True),
        sa.Column('transferencia_destino_conta_id', sa.Integer(), nullable=True),
        sa.Column('categoria_dre_id', sa.Integer(), nullable=True),
        sa.Column('centro_custo_id', sa.Integer(), nullable=True),
        
        # Recorrência
        sa.Column('recorrente', sa.Boolean(), default=False),
        sa.Column('periodicidade', sa.String(20), nullable=True),  # 'mensal', 'anual', etc
        sa.Column('grupo_recorrencia', sa.UUID(), nullable=True),
        
        # Auditoria
        sa.Column('classificado_por', sa.Integer(), nullable=True),  # user_id
        sa.Column('classificado_em', sa.DateTime(), nullable=True),
        sa.Column('regra_aplicada_id', sa.UUID(), nullable=True),
        
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['extrato_id'], ['extratos_bancarios.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['conta_bancaria_id'], ['contas_bancarias.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conta_pagar_id'], ['contas_pagar.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['conta_receber_id'], ['contas_receber.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_movimentacoes_tenant', 'movimentacoes_bancarias', ['tenant_id'])
    op.create_index('ix_movimentacoes_extrato', 'movimentacoes_bancarias', ['extrato_id'])
    op.create_index('ix_movimentacoes_status', 'movimentacoes_bancarias', ['status_conciliacao'])
    op.create_index('ix_movimentacoes_fitid', 'movimentacoes_bancarias', ['fitid'])
    op.create_index('ix_movimentacoes_data', 'movimentacoes_bancarias', ['data_movimento'])
    
    # Tabela: regras_conciliacao
    op.create_table(
        'regras_conciliacao',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        
        # Padrão de reconhecimento
        sa.Column('padrao_memo', sa.String(255), nullable=True),  # Ex: "%MANFRIM%"
        sa.Column('tipo_operacao', sa.String(50), nullable=True),  # 'Pagamento', 'Pix', 'Taxa'
        sa.Column('valor_min', sa.Numeric(15, 2), nullable=True),
        sa.Column('valor_max', sa.Numeric(15, 2), nullable=True),
        
        # Ação automática
        sa.Column('tipo_vinculo', sa.String(50), nullable=True),
        sa.Column('fornecedor_id', sa.Integer(), nullable=True),
        sa.Column('categoria_dre_id', sa.Integer(), nullable=True),
        sa.Column('criar_conta_pagar', sa.Boolean(), default=False),
        sa.Column('baixar_automatico', sa.Boolean(), default=False),
        
        # Recorrência
        sa.Column('recorrente', sa.Boolean(), default=False),
        sa.Column('periodicidade', sa.String(20), nullable=True),
        sa.Column('criar_provisoes', sa.Boolean(), default=False),
        sa.Column('meses_provisao', sa.Integer(), default=12),
        
        # Confiabilidade
        sa.Column('vezes_aplicada', sa.Integer(), default=0),
        sa.Column('vezes_confirmada', sa.Integer(), default=0),
        sa.Column('confianca', sa.Integer(), nullable=True),  # (confirmada/aplicada) * 100
        
        # Status
        sa.Column('ativa', sa.Boolean(), default=True),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_regras_tenant', 'regras_conciliacao', ['tenant_id'])
    op.create_index('ix_regras_ativa', 'regras_conciliacao', ['ativa'])
    op.create_index('ix_regras_confianca', 'regras_conciliacao', ['confianca'])
    
    # Tabela: provisoes_automaticas
    op.create_table(
        'provisoes_automaticas',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('regra_id', sa.UUID(), nullable=True),
        
        sa.Column('conta_pagar_id', sa.Integer(), nullable=True),  # Provisão criada
        sa.Column('data_vencimento', sa.Date(), nullable=True),
        sa.Column('valor', sa.Numeric(15, 2), nullable=True),
        sa.Column('descricao', sa.Text(), nullable=True),
        
        sa.Column('status', sa.String(50), nullable=True),  # 'provisionado', 'realizado', 'cancelado'
        sa.Column('movimentacao_real_id', sa.UUID(), nullable=True),  # Quando realiza, vincula
        
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['regra_id'], ['regras_conciliacao.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['conta_pagar_id'], ['contas_pagar.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['movimentacao_real_id'], ['movimentacoes_bancarias.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_provisoes_tenant', 'provisoes_automaticas', ['tenant_id'])
    op.create_index('ix_provisoes_status', 'provisoes_automaticas', ['status'])
    op.create_index('ix_provisoes_vencimento', 'provisoes_automaticas', ['data_vencimento'])
    
    # Tabela: templates_adquirentes
    op.create_table(
        'templates_adquirentes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        
        # Identificação
        sa.Column('nome_adquirente', sa.String(100), nullable=True),  # 'Stone', 'Cielo', 'Rede', etc
        sa.Column('tipo_relatorio', sa.String(50), nullable=True),  # 'vendas', 'recebimentos', 'extrato'
        
        # Mapeamento de colunas (JSON)
        sa.Column('mapeamento', sa.JSON(), nullable=True),
        
        # Detecção automática
        sa.Column('palavras_chave', sa.JSON(), nullable=True),  # ['stone', 'pagamentos']
        sa.Column('colunas_obrigatorias', sa.JSON(), nullable=True),
        
        # Uso
        sa.Column('vezes_usado', sa.Integer(), default=0),
        sa.Column('ultima_utilizacao', sa.DateTime(), nullable=True),
        sa.Column('auto_aplicar', sa.Boolean(), default=True),
        
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('criado_por', sa.UUID(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_templates_tenant', 'templates_adquirentes', ['tenant_id'])
    op.create_index('ix_templates_adquirente', 'templates_adquirentes', ['nome_adquirente'])


def downgrade() -> None:
    """Downgrade schema - Remove tabelas de conciliação bancária."""
    op.drop_table('templates_adquirentes')
    op.drop_table('provisoes_automaticas')
    op.drop_table('regras_conciliacao')
    op.drop_table('movimentacoes_bancarias')
    op.drop_table('extratos_bancarios')
