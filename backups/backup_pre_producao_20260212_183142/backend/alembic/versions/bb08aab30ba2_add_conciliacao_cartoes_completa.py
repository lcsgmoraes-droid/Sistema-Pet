"""add_conciliacao_cartoes_completa

Revision ID: bb08aab30ba2
Revises: 7c3307a9c117
Create Date: 2026-02-11 10:18:35.609169

FASE 1: FUNDAÇÃO - CONCILIAÇÃO DE CARTÕES
-------------------------------------------
Implementa estrutura completa para conciliação de cartões com validação em cascata.

Baseado em:
- docs/ARQUITETURA_CONCILIACAO_CARTOES.md
- docs/ROADMAP_CONCILIACAO_CARTOES.md

Tabelas criadas:
1. empresa_parametros - Parâmetros configuráveis (tolerâncias, etc)
2. adquirentes_templates - Templates para parsear CSVs de diferentes operadoras
3. arquivos_evidencia - Armazena metadados dos arquivos importados
4. conciliacao_importacoes - Dados brutos importados (OFX, CSVs)
5. conciliacao_lotes - Lotes de pagamento/transferências
6. conciliacao_validacoes - Resultado da validação em cascata
7. conciliacao_logs - Log completo de auditoria

Alterações em tabelas existentes:
- contas_receber: novos campos para status, taxas reais/estimadas, versionamento
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bb08aab30ba2'
down_revision: Union[str, Sequence[str], None] = '7c3307a9c117'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Conciliação de Cartões Completa."""
    
    # ==========================================================================
    # 1. EMPRESA_PARAMETROS - Parâmetros configuráveis por empresa
    # ==========================================================================
    op.create_table(
        'empresa_parametros',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', UUID(), nullable=False),
        
        # Tolerâncias de conciliação (Ajuste #2)
        sa.Column('tolerancia_conciliacao', sa.Numeric(10, 2), default=0.10, nullable=False, 
                  comment='Tolerância automática (ex: 0.01, 0.50, 5.00)'),
        sa.Column('tolerancia_conciliacao_media', sa.Numeric(10, 2), default=10.00, nullable=False,
                  comment='Tolerância média - requer confirmação (ex: 10.00)'),
        
        # Configurações de conciliação
        sa.Column('dias_vencimento_cartao_debito', sa.Integer(), default=1,
                  comment='D+1 = amanhã'),
        sa.Column('dias_vencimento_cartao_credito_av', sa.Integer(), default=30,
                  comment='D+30 para crédito à vista'),
        
        # Taxas estimadas padrão (usado quando não há tabela de taxas)
        sa.Column('taxa_mdr_debito_estimada', sa.Numeric(5, 2), default=1.59),
        sa.Column('taxa_mdr_credito_av_estimada', sa.Numeric(5, 2), default=3.79),
        sa.Column('taxa_mdr_credito_parcelado_estimada', sa.Numeric(5, 2), default=5.20),
        
        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), 
                  onupdate=sa.text('CURRENT_TIMESTAMP')),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', name='uq_empresa_parametros_tenant'),
    )
    op.create_index('ix_empresa_parametros_tenant', 'empresa_parametros', ['tenant_id'])
    
    # ==========================================================================
    # 2. ADQUIRENTES_TEMPLATES - Templates para parsear CSVs (Ajuste #11)
    # ==========================================================================
    op.create_table(
        'adquirentes_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', UUID(), nullable=False),
        
        # Identificação
        sa.Column('nome', sa.String(100), nullable=False, comment='Stone, Cielo, Rede, Getnet, etc'),
        sa.Column('tipo_arquivo', sa.String(50), nullable=False, comment='recebimentos, pagamentos, vendas'),
        sa.Column('ativo', sa.Boolean(), default=True),
        
        # Configuração do parser
        sa.Column('separador', sa.String(5), default=';', nullable=False),
        sa.Column('encoding', sa.String(20), default='utf-8', nullable=False),
        sa.Column('tem_header', sa.Boolean(), default=True),
        sa.Column('pular_linhas', sa.Integer(), default=0, comment='Pular N linhas iniciais'),
        
        # Mapeamento de colunas (JSONB para flexibilidade)
        sa.Column('mapeamento', postgresql.JSONB(), nullable=False, comment='''
        Exemplo Stone Recebimentos:
        {
            "nsu": "STONE ID",
            "valor_bruto": "VALOR BRUTO",
            "valor_liquido": "VALOR LÍQUIDO",
            "taxa_mdr": "DESCONTO DE MDR",
            "taxa_antecipacao": "DESCONTO DE ANTECIPAÇÃO",
            "data_venda": "DATA DA VENDA",
            "data_vencimento": "DATA DE VENCIMENTO",
            "bandeira": "BANDEIRA",
            "produto": "PRODUTO",
            "status": "ÚLTIMO STATUS"
        }
        '''),
        
        # Transformações (opcional)
        sa.Column('transformacoes', postgresql.JSONB(), nullable=True, comment='''
        Regras de transformação por campo:
        {
            "valor_bruto": {"tipo": "decimal", "formato": ","},
            "data_venda": {"tipo": "data", "formato": "DD/MM/YYYY HH:mm"}
        }
        '''),
        
        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('criado_por_id', sa.Integer(), nullable=True),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['criado_por_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_adquirentes_templates_tenant', 'adquirentes_templates', ['tenant_id'])
    op.create_index('ix_adquirentes_templates_nome', 'adquirentes_templates', ['nome', 'tipo_arquivo'])
    
    # ==========================================================================
    # 3. ARQUIVOS_EVIDENCIA - Armazena metadados dos arquivos (Ajuste #6)
    # ==========================================================================
    op.create_table(
        'arquivos_evidencia',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', UUID(), nullable=False),
        
        # Identificação do arquivo
        sa.Column('nome_original', sa.String(255), nullable=False),
        sa.Column('tipo_arquivo', sa.String(50), nullable=False, comment='ofx, recebimentos, pagamentos, vendas'),
        sa.Column('adquirente', sa.String(100), nullable=True, comment='Stone, Cielo, etc'),
        
        # Armazenamento
        sa.Column('caminho_storage', sa.String(500), nullable=False, comment='Caminho no storage/S3'),
        sa.Column('tamanho_bytes', sa.BigInteger(), nullable=True),
        sa.Column('hash_md5', sa.String(32), nullable=False, comment='Para detectar duplicatas'),
        sa.Column('hash_sha256', sa.String(64), nullable=True, comment='Segurança adicional'),
        
        # Metadados do conteúdo
        sa.Column('periodo_inicio', sa.Date(), nullable=True),
        sa.Column('periodo_fim', sa.Date(), nullable=True),
        sa.Column('total_linhas', sa.Integer(), nullable=True),
        sa.Column('total_registros_processados', sa.Integer(), nullable=True),
        
        # Auditoria (Ajuste #8)
        sa.Column('criado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('criado_por_id', sa.Integer(), nullable=False),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['criado_por_id'], ['users.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_arquivos_evidencia_tenant', 'arquivos_evidencia', ['tenant_id'])
    op.create_index('ix_arquivos_evidencia_hash', 'arquivos_evidencia', ['hash_md5'])
    op.create_index('ix_arquivos_evidencia_periodo', 'arquivos_evidencia', ['periodo_inicio', 'periodo_fim'])
    
    # ==========================================================================
    # 4. CONCILIACAO_IMPORTACOES - Dados brutos importados (Separação Etapa 1)
    # ==========================================================================
    op.create_table(
        'conciliacao_importacoes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', UUID(), nullable=False),
        
        # Referência ao arquivo
        sa.Column('arquivo_evidencia_id', sa.Integer(), nullable=False),
        sa.Column('adquirente_template_id', sa.Integer(), nullable=True, 
                  comment='NULL para OFX (não usa template)'),
        
        # Tipo de importação
        sa.Column('tipo_importacao', sa.String(50), nullable=False, 
                  comment='ofx_creditos, pagamentos_lotes, recebimentos_detalhados'),
        sa.Column('data_referencia', sa.Date(), nullable=False, comment='Data do movimento/crédito'),
        
        # Dados agregados da importação
        sa.Column('total_registros', sa.Integer(), default=0),
        sa.Column('total_valor', sa.Numeric(15, 2), default=0),
        sa.Column('status_importacao', sa.String(50), default='pendente', 
                  comment='pendente, processada, erro, cancelada'),
        
        # Resumo do conteúdo (JSONB flexível)
        sa.Column('resumo', postgresql.JSONB(), nullable=True, comment='''
        Exemplo OFX:
        {
            "total_creditos": 16,
            "total_debitos": 5,
            "valor_creditos": 1820.00,
            "valor_debitos": 150.00
        }
        '''),
        
        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('criado_por_id', sa.Integer(), nullable=False),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['arquivo_evidencia_id'], ['arquivos_evidencia.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['adquirente_template_id'], ['adquirentes_templates.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['criado_por_id'], ['users.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_conciliacao_importacoes_tenant', 'conciliacao_importacoes', ['tenant_id'])
    op.create_index('ix_conciliacao_importacoes_data', 'conciliacao_importacoes', ['data_referencia'])
    op.create_index('ix_conciliacao_importacoes_tipo', 'conciliacao_importacoes', ['tipo_importacao'])
    
    # ==========================================================================
    # 5. CONCILIACAO_LOTES - Lotes de pagamento/transferências (Ajuste #3)
    # ==========================================================================
    op.create_table(
        'conciliacao_lotes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', UUID(), nullable=False),
        
        # Vínculo com importação
        sa.Column('importacao_pagamentos_id', sa.Integer(), nullable=True,
                  comment='Importação do comprovante de pagamentos'),
        sa.Column('importacao_ofx_id', sa.Integer(), nullable=True,
                  comment='Importação do OFX (se validado)'),
        
        # Identificação do lote
        sa.Column('adquirente', sa.String(100), nullable=False),
        sa.Column('identificador_lote', sa.String(255), nullable=True, 
                  comment='ID fornecido pela operadora (se existir)'),
        sa.Column('data_pagamento', sa.Date(), nullable=False),
        
        # Valores
        sa.Column('valor_bruto', sa.Numeric(15, 2), nullable=False),
        sa.Column('valor_liquido', sa.Numeric(15, 2), nullable=False),
        sa.Column('valor_descontos', sa.Numeric(15, 2), default=0),
        
        # Classificação (Ajuste #1 - estados)
        sa.Column('bandeira', sa.String(50), nullable=True, comment='Visa, Master, Elo, etc'),
        sa.Column('modalidade', sa.String(50), nullable=True, comment='Antecipação, Débito, Crédito'),
        
        # Status do lote (Ajuste #3)
        sa.Column('status_lote', sa.String(50), default='previsto', 
                  comment='previsto, informado, creditado, divergente'),
        
        # Quantidade de parcelas no lote
        sa.Column('quantidade_parcelas', sa.Integer(), default=0,
                  comment='Quantas ContaReceber fazem parte deste lote'),
        
        # Vínculo com movimentação bancária (se OFX disponível)
        sa.Column('movimentacao_bancaria_id', sa.Integer(), nullable=True),
        
        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['importacao_pagamentos_id'], ['conciliacao_importacoes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['importacao_ofx_id'], ['conciliacao_importacoes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['movimentacao_bancaria_id'], ['movimentacoes_bancarias.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_conciliacao_lotes_tenant', 'conciliacao_lotes', ['tenant_id'])
    op.create_index('ix_conciliacao_lotes_data', 'conciliacao_lotes', ['data_pagamento'])
    op.create_index('ix_conciliacao_lotes_status', 'conciliacao_lotes', ['status_lote'])
    op.create_index('ix_conciliacao_lotes_adquirente', 'conciliacao_lotes', ['adquirente'])
    
    # ==========================================================================
    # 6. CONCILIACAO_VALIDACOES - Resultado da validação em cascata
    # ==========================================================================
    op.create_table(
        'conciliacao_validacoes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', UUID(), nullable=False),
        
        # Referências às importações validadas
        sa.Column('importacao_ofx_id', sa.Integer(), nullable=True),
        sa.Column('importacao_pagamentos_id', sa.Integer(), nullable=True),
        sa.Column('importacao_recebimentos_id', sa.Integer(), nullable=True),
        
        # Data da validação
        sa.Column('data_referencia', sa.Date(), nullable=False),
        sa.Column('adquirente', sa.String(100), nullable=False),
        
        # Totais validados
        sa.Column('total_ofx', sa.Numeric(15, 2), nullable=True),
        sa.Column('total_pagamentos', sa.Numeric(15, 2), nullable=True),
        sa.Column('total_recebimentos', sa.Numeric(15, 2), nullable=True),
        
        # Resultado da validação em cascata (Ajuste #12)
        sa.Column('diferenca_ofx_pagamentos', sa.Numeric(15, 2), default=0),
        sa.Column('diferenca_pagamentos_recebimentos', sa.Numeric(15, 2), default=0),
        sa.Column('percentual_divergencia', sa.Numeric(5, 2), default=0),
        
        # Classificação (Ajuste #4 - nunca bloquear)
        sa.Column('confianca', sa.String(20), nullable=False, 
                  comment='ALTA, MEDIA, BAIXA'),
        sa.Column('pode_processar', sa.Boolean(), default=True, 
                  comment='Sempre True - sistema nunca bloqueia'),
        sa.Column('requer_confirmacao', sa.Boolean(), default=False),
        
        # Status da validação (Ajuste #3)
        sa.Column('status_validacao', sa.String(50), default='pendente',
                  comment='pendente, parcial, concluida, divergente'),
        
        # Alertas gerados (JSONB array)
        sa.Column('alertas', postgresql.JSONB(), nullable=True, comment='''
        [
            {
                "tipo": "info|warning|error",
                "codigo": "NSU_ORFAO",
                "mensagem": "5 NSUs encontrados no arquivo mas não no sistema",
                "detalhes": {...}
            }
        ]
        '''),
        
        # Parcelas e lotes envolvidos
        sa.Column('quantidade_parcelas', sa.Integer(), default=0),
        sa.Column('quantidade_lotes', sa.Integer(), default=0),
        sa.Column('parcelas_confirmadas', sa.Integer(), default=0),
        sa.Column('parcelas_orfas', sa.Integer(), default=0),
        
        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('criado_por_id', sa.Integer(), nullable=False),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['importacao_ofx_id'], ['conciliacao_importacoes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['importacao_pagamentos_id'], ['conciliacao_importacoes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['importacao_recebimentos_id'], ['conciliacao_importacoes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['criado_por_id'], ['users.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_conciliacao_validacoes_tenant', 'conciliacao_validacoes', ['tenant_id'])
    op.create_index('ix_conciliacao_validacoes_data', 'conciliacao_validacoes', ['data_referencia'])
    op.create_index('ix_conciliacao_validacoes_status', 'conciliacao_validacoes', ['status_validacao'])
    op.create_index('ix_conciliacao_validacoes_confianca', 'conciliacao_validacoes', ['confianca'])
    
    # ==========================================================================
    # 7. CONCILIACAO_LOGS - Log completo de auditoria (Ajustes #7, #8)
    # ==========================================================================
    op.create_table(
        'conciliacao_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', UUID(), nullable=False),
        
        # Vínculo com validação (se processamento)
        sa.Column('conciliacao_validacao_id', sa.Integer(), nullable=True),
        
        # Versionamento (Ajuste #7)
        sa.Column('versao_conciliacao', sa.Integer(), default=1, nullable=False,
                  comment='Incrementa a cada reprocessamento'),
        
        # Ação realizada
        sa.Column('acao', sa.String(100), nullable=False,
                  comment='importar_ofx, processar_conciliacao, reverter_conciliacao, etc'),
        sa.Column('status_acao', sa.String(50), default='sucesso',
                  comment='sucesso, erro, parcial, revertido'),
        
        # Detalhes da ação (JSONB flexível)
        sa.Column('arquivos_utilizados', postgresql.JSONB(), nullable=True, comment='''
        {
            "ofx": "extrato_20260210.ofx",
            "pagamentos": "comprovante_09_10_fev.csv",
            "recebimentos": "relatorio_recebimentos_fev.csv"
        }
        '''),
        
        sa.Column('quantidades', postgresql.JSONB(), nullable=True, comment='''
        {
            "parcelas_liquidadas": 26,
            "lotes_conciliados": 16,
            "creditos_ofx": 16,
            "valor_total": 1820.00
        }
        '''),
        
        sa.Column('diferencas', postgresql.JSONB(), nullable=True, comment='''
        {
            "ofx_vs_pagamentos": 0.00,
            "pagamentos_vs_recebimentos": 0.01,
            "percentual": 0.0005
        }
        '''),
        
        # Motivo (para reversões ou decisões manuais)
        sa.Column('motivo', sa.Text(), nullable=True,
                  comment='Preenchido em reversões ou confirmações com divergência'),
        
        # Auditoria completa (Ajuste #8)
        sa.Column('criado_em', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('criado_por_id', sa.Integer(), nullable=False),
        sa.Column('ip_origem', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conciliacao_validacao_id'], ['conciliacao_validacoes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['criado_por_id'], ['users.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_conciliacao_logs_tenant', 'conciliacao_logs', ['tenant_id'])
    op.create_index('ix_conciliacao_logs_validacao', 'conciliacao_logs', ['conciliacao_validacao_id'])
    op.create_index('ix_conciliacao_logs_acao', 'conciliacao_logs', ['acao'])
    op.create_index('ix_conciliacao_logs_criado_em', 'conciliacao_logs', ['criado_em'])
    op.create_index('ix_conciliacao_logs_versao', 'conciliacao_logs', ['versao_conciliacao'])
    
    # ==========================================================================
    # 8. ATUALIZAR CONTAS_RECEBER - Novos campos (Ajustes #1, #6, #7, #13)
    # ==========================================================================
    
    # Status de conciliação (Ajuste #1 - com aguardando_lote)
    op.add_column('contas_receber', 
        sa.Column('status_conciliacao', sa.String(50), default='prevista',
                  comment='prevista|confirmada_operadora|aguardando_lote|em_lote|liquidada'))
    
    # Taxas ESTIMADAS (calculadas no PDV)
    op.add_column('contas_receber',
        sa.Column('taxa_mdr_estimada', sa.Numeric(15, 2), default=0,
                  comment='Taxa MDR estimada no momento da venda'))
    op.add_column('contas_receber',
        sa.Column('taxa_antecipacao_estimada', sa.Numeric(15, 2), default=0,
                  comment='Taxa antecipação estimada (geralmente 0 se não antecipado)'))
    op.add_column('contas_receber',
        sa.Column('valor_liquido_estimado', sa.Numeric(15, 2), nullable=True,
                  comment='Valor líquido estimado (bruto - taxas estimadas)'))
    op.add_column('contas_receber',
        sa.Column('data_vencimento_estimada', sa.Date(), nullable=True,
                  comment='Data vencimento calculada (D+1 débito, D+30 crédito)'))
    
    # Taxas REAIS (atualizadas ao importar recebimentos) - Ajuste #13
    op.add_column('contas_receber',
        sa.Column('taxa_mdr_real', sa.Numeric(15, 2), nullable=True,
                  comment='Taxa MDR real cobrada (do arquivo operadora)'))
    op.add_column('contas_receber',
        sa.Column('taxa_antecipacao_real', sa.Numeric(15, 2), nullable=True,
                  comment='Taxa antecipação real cobrada'))
    op.add_column('contas_receber',
        sa.Column('valor_liquido_real', sa.Numeric(15, 2), nullable=True,
                  comment='Valor líquido real (do arquivo operadora)'))
    op.add_column('contas_receber',
        sa.Column('data_vencimento_real', sa.Date(), nullable=True,
                  comment='Data vencimento real (do arquivo operadora)'))
    
    # Diferenças para alertas (Ajuste #13)
    op.add_column('contas_receber',
        sa.Column('diferenca_taxa', sa.Numeric(15, 2), nullable=True,
                  comment='real - estimada (alerta se significativo)'))
    op.add_column('contas_receber',
        sa.Column('diferenca_valor', sa.Numeric(15, 2), nullable=True,
                  comment='Diferença valor líquido'))
    
    # Vínculo com lote (quando incluída em pagamento)
    op.add_column('contas_receber',
        sa.Column('conciliacao_lote_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_contas_receber_lote', 'contas_receber', 'conciliacao_lotes',
        ['conciliacao_lote_id'], ['id'], ondelete='SET NULL'
    )
    
    # Versionamento para rastrear reprocessamentos (Ajuste #7)
    op.add_column('contas_receber',
        sa.Column('versao_conciliacao', sa.Integer(), default=0,
                  comment='Incrementa cada vez que é reprocessada'))
    
    # Data de liquidação efetiva (quando crédito confirmado)
    op.add_column('contas_receber',
        sa.Column('data_liquidacao', sa.Date(), nullable=True,
                  comment='Data que realmente creditou (do OFX)'))
    
    # Índices para performance
    op.create_index('ix_contas_receber_status_conciliacao', 'contas_receber', ['status_conciliacao'])
    op.create_index('ix_contas_receber_lote', 'contas_receber', ['conciliacao_lote_id'])
    op.create_index('ix_contas_receber_versao', 'contas_receber', ['versao_conciliacao'])


def downgrade() -> None:
    """Downgrade schema - Remove conciliação de cartões."""
    
    # Reverter contas_receber
    op.drop_index('ix_contas_receber_versao', 'contas_receber')
    op.drop_index('ix_contas_receber_lote', 'contas_receber')
    op.drop_index('ix_contas_receber_status_conciliacao', 'contas_receber')
    
    op.drop_constraint('fk_contas_receber_lote', 'contas_receber', type_='foreignkey')
    
    op.drop_column('contas_receber', 'data_liquidacao')
    op.drop_column('contas_receber', 'versao_conciliacao')
    op.drop_column('contas_receber', 'conciliacao_lote_id')
    op.drop_column('contas_receber', 'diferenca_valor')
    op.drop_column('contas_receber', 'diferenca_taxa')
    op.drop_column('contas_receber', 'data_vencimento_real')
    op.drop_column('contas_receber', 'valor_liquido_real')
    op.drop_column('contas_receber', 'taxa_antecipacao_real')
    op.drop_column('contas_receber', 'taxa_mdr_real')
    op.drop_column('contas_receber', 'data_vencimento_estimada')
    op.drop_column('contas_receber', 'valor_liquido_estimado')
    op.drop_column('contas_receber', 'taxa_antecipacao_estimada')
    op.drop_column('contas_receber', 'taxa_mdr_estimada')
    op.drop_column('contas_receber', 'status_conciliacao')
    
    # Dropar tabelas na ordem reversa
    op.drop_table('conciliacao_logs')
    op.drop_table('conciliacao_validacoes')
    op.drop_table('conciliacao_lotes')
    op.drop_table('conciliacao_importacoes')
    op.drop_table('arquivos_evidencia')
    op.drop_table('adquirentes_templates')
    op.drop_table('empresa_parametros')

