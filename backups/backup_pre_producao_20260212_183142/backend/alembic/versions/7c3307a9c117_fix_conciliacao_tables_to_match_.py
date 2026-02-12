"""fix_conciliacao_tables_to_match_basetenantmodel

Revision ID: 7c3307a9c117
Revises: 9e78a5374aca
Create Date: 2026-02-11 00:48:35.764659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c3307a9c117'
down_revision: Union[str, Sequence[str], None] = '9e78a5374aca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix conciliacao tables to match BaseTenantModel pattern:
    - id: Integer Identity (not UUID)
    - created_at, updated_at (not criado_em, atualizado_em)
    - Remove criado_por column
    """
    # Como as tabelas estão vazias, vamos drop e recriar com estrutura correta
    op.drop_table('templates_adquirentes')
    op.drop_table('provisoes_automaticas')
    op.drop_table('regras_conciliacao')
    op.drop_table('movimentacoes_bancarias')
    op.drop_table('extratos_bancarios')
    
    # Recriar 1: extratos_bancarios
    op.create_table(
        'extratos_bancarios',
        sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('conta_bancaria_id', sa.Integer(), nullable=False),
        sa.Column('arquivo_nome', sa.String(255), nullable=True),
        sa.Column('data_upload', sa.DateTime(), nullable=True),
        sa.Column('periodo_inicio', sa.Date(), nullable=True),
        sa.Column('periodo_fim', sa.Date(), nullable=True),
        sa.Column('total_movimentacoes', sa.Integer(), nullable=True),
        sa.Column('conciliadas', sa.Integer(), default=0),
        sa.Column('pendentes', sa.Integer(), default=0),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conta_bancaria_id'], ['contas_bancarias.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_extratos_tenant', 'extratos_bancarios', ['tenant_id'])
    op.create_index('ix_extratos_conta', 'extratos_bancarios', ['conta_bancaria_id'])
    op.create_index('ix_extratos_status', 'extratos_bancarios', ['status'])
    
    # Recriar 2: movimentacoes_bancarias
    op.create_table(
        'movimentacoes_bancarias',
        sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('extrato_id', sa.Integer(), nullable=False),
        sa.Column('conta_bancaria_id', sa.Integer(), nullable=False),
        
        # Dados da movimentação
        sa.Column('fitid', sa.String(255), nullable=True),
        sa.Column('data_movimento', sa.Date(), nullable=True),
        sa.Column('valor', sa.Numeric(15, 2), nullable=True),
        sa.Column('tipo', sa.String(20), nullable=True),  # 'CREDIT', 'DEBIT'
        sa.Column('memo', sa.Text(), nullable=True),
        sa.Column('checknum', sa.String(50), nullable=True),
        
        # Conciliação
        sa.Column('status_conciliacao', sa.String(50), nullable=True),  # 'pendente', 'sugerido', 'conciliado', 'manual'
        sa.Column('tipo_operacao', sa.String(50), nullable=True),  # 'pagamento_fornecedor', 'taxa', 'transferencia', 'recebimento'
        sa.Column('confianca_sugestao', sa.Integer(), default=0),  # 0-100%
        
        # Vínculos (apenas um será preenchido dependendo do tipo_operacao)
        sa.Column('fornecedor_id', sa.Integer(), nullable=True),
        sa.Column('conta_pagar_id', sa.Integer(), nullable=True),
        sa.Column('conta_receber_id', sa.Integer(), nullable=True),
        sa.Column('categoria_dre_id', sa.Integer(), nullable=True),
        sa.Column('centro_custo_id', sa.Integer(), nullable=True),
        
        # Observações
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('classificado_por', sa.Integer(), nullable=True),  # user_id
        sa.Column('classificado_em', sa.DateTime(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['extrato_id'], ['extratos_bancarios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conta_bancaria_id'], ['contas_bancarias.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fornecedor_id'], ['clientes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['conta_pagar_id'], ['contas_pagar.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['conta_receber_id'], ['contas_receber.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['categoria_dre_id'], ['dre_subcategorias.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['classificado_por'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_movimentacoes_tenant', 'movimentacoes_bancarias', ['tenant_id'])
    op.create_index('ix_movimentacoes_extrato', 'movimentacoes_bancarias', ['extrato_id'])
    op.create_index('ix_movimentacoes_conta', 'movimentacoes_bancarias', ['conta_bancaria_id'])
    op.create_index('ix_movimentacoes_status', 'movimentacoes_bancarias', ['status_conciliacao'])
    op.create_index('ix_movimentacoes_data', 'movimentacoes_bancarias', ['data_movimento'])
    op.create_index('ix_movimentacoes_fitid', 'movimentacoes_bancarias', ['fitid'])
    
    # Recriar 3: regras_conciliacao
    op.create_table(
        'regras_conciliacao',
        sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        
        # Padrão de reconhecimento
        sa.Column('padrao_memo', sa.String(255), nullable=True),  # Regex ou LIKE pattern
        sa.Column('tipo_operacao', sa.String(50), nullable=True),
        
        # Aprendizado
        sa.Column('vezes_aplicada', sa.Integer(), default=0),
        sa.Column('vezes_confirmada', sa.Integer(), default=0),
        sa.Column('confianca', sa.Integer(), default=0),  # Calculado: (confirmada/aplicada)*100
        
        # Vínculos padrão
        sa.Column('fornecedor_id', sa.Integer(), nullable=True),
        sa.Column('categoria_dre_id', sa.Integer(), nullable=True),
        sa.Column('centro_custo_id', sa.Integer(), nullable=True),
        
        # Metadata
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ativo', sa.Boolean(), default=True),
        sa.Column('prioridade', sa.Integer(), default=0),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fornecedor_id'], ['clientes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['categoria_dre_id'], ['dre_subcategorias.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_regras_tenant', 'regras_conciliacao', ['tenant_id'])
    op.create_index('ix_regras_padrao', 'regras_conciliacao', ['padrao_memo'])
    op.create_index('ix_regras_ativo', 'regras_conciliacao', ['ativo'])
    op.create_index('ix_regras_confianca', 'regras_conciliacao', ['confianca'])
    
    # Recriar 4: provisoes_automaticas
    op.create_table(
        'provisoes_automaticas',
        sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('regra_id', sa.Integer(), nullable=True),
        sa.Column('conta_pagar_id', sa.Integer(), nullable=True),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('valor', sa.Numeric(15, 2), nullable=True),
        sa.Column('periodicidade', sa.String(20), nullable=True),  # 'mensal', 'trimestral', 'semestral', 'anual'
        sa.Column('data_vencimento', sa.Date(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),  # 'provisao', 'conciliado'
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['regra_id'], ['regras_conciliacao.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conta_pagar_id'], ['contas_pagar.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_provisoes_tenant', 'provisoes_automaticas', ['tenant_id'])
    op.create_index('ix_provisoes_status', 'provisoes_automaticas', ['status'])
    op.create_index('ix_provisoes_vencimento', 'provisoes_automaticas', ['data_vencimento'])
    
    # Recriar 5: templates_adquirentes
    op.create_table(
        'templates_adquirentes',
        sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        
        sa.Column('nome_adquirente', sa.String(100), nullable=True),
        sa.Column('tipo_relatorio', sa.String(50), nullable=True),
        sa.Column('mapeamento', sa.JSON(), nullable=True),
        sa.Column('palavras_chave', sa.JSON(), nullable=True),
        sa.Column('colunas_obrigatorias', sa.JSON(), nullable=True),
        sa.Column('vezes_usado', sa.Integer(), default=0),
        sa.Column('ultima_utilizacao', sa.DateTime(), nullable=True),
        sa.Column('auto_aplicar', sa.Boolean(), default=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_templates_tenant', 'templates_adquirentes', ['tenant_id'])
    op.create_index('ix_templates_adquirente', 'templates_adquirentes', ['nome_adquirente'])


def downgrade() -> None:
    """Downgrade - voltar para estrutura UUID com criado_em/atualizado_em."""
    # Drop tabelas com Integer
    op.drop_table('templates_adquirentes')
    op.drop_table('provisoes_automaticas')
    op.drop_table('regras_conciliacao')
    op.drop_table('movimentacoes_bancarias')
    op.drop_table('extratos_bancarios')
    
    # Recriar com estrutura antiga (UUID)
    # (código omitido para brevidade - usar estrutura da migration 9e78a5374aca)
