"""
Models para Conciliação de Cartões - Fase 1

Implementa estrutura completa para conciliação de cartões com validação em cascata.

Baseado em:
- docs/ARQUITETURA_CONCILIACAO_CARTOES.md
- docs/ROADMAP_CONCILIACAO_CARTOES.md  
- docs/AJUSTES_ARQUITETURA_APLICADOS.md

Models criados:
1. EmpresaParametros - Parâmetros configuráveis (tolerâncias, taxas estimadas)
2. AdquirenteTemplate - Templates para parsear CSVs de operadoras
3. ArquivoEvidencia - Metadados dos arquivos importados
4. ConciliacaoImportacao - Dados brutos importados (OFX, CSV)
5. ConciliacaoLote - Lotes de pagamento/transferências
6. ConciliacaoValidacao - Resultado da validação em cascata
7. ConciliacaoLog - Log completo de auditoria
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey, Numeric, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from decimal import Decimal

from .db import Base
from .base_models import BaseTenantModel


# ==============================================================================
# EMPRESA_PARAMETROS - Configurações por empresa (Ajuste #2)
# ==============================================================================

class EmpresaParametros(Base):
    """
    Parâmetros configuráveis por empresa/tenant.
    
    Ajuste #2: Tolerância não pode ser hardcoded - cada empresa decide.
    Suporta clientes com arrendondamentos diferentes (redes grandes, pequenos negócios).
    
    ⚠️ IMPORTANTE: Não herda de BaseTenantModel para evitar conflito created_at/criado_em.
    """
    __tablename__ = "empresa_parametros"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Tolerâncias de conciliação (configuráveis)
    tolerancia_conciliacao = Column(
        Numeric(10, 2), 
        default=Decimal('0.10'), 
        nullable=False,
        comment="Tolerância automática - processamento sem confirmação (ex: 0.01, 0.50, 5.00)"
    )
    tolerancia_conciliacao_media = Column(
        Numeric(10, 2),
        default=Decimal('10.00'),
        nullable=False,
        comment="Tolerância média - requer confirmação simples (ex: 10.00)"
    )
    
    # Vencimentos padrão
    dias_vencimento_cartao_debito = Column(
        Integer,
        default=1,
        comment="D+1 = amanhã"
    )
    dias_vencimento_cartao_credito_av = Column(
        Integer,
        default=30,
        comment="D+30 para crédito à vista"
    )
    
    # Taxas MDR estimadas (quando não há tabela específica)
    taxa_mdr_debito_estimada = Column(Numeric(5, 2), default=Decimal('1.59'))
    taxa_mdr_credito_av_estimada = Column(Numeric(5, 2), default=Decimal('3.79'))
    taxa_mdr_credito_parcelado_estimada = Column(Numeric(5, 2), default=Decimal('5.20'))
    
    # Auditoria
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Serialização para JSON"""
        return {
            'id': self.id,
            'tenant_id': str(self.tenant_id),
            'tolerancias': {
                'automatica': float(self.tolerancia_conciliacao),
                'media': float(self.tolerancia_conciliacao_media)
            },
            'vencimentos': {
                'debito_dias': self.dias_vencimento_cartao_debito,
                'credito_av_dias': self.dias_vencimento_cartao_credito_av
            },
            'taxas_estimadas': {
                'debito_mdr': float(self.taxa_mdr_debito_estimada),
                'credito_av_mdr': float(self.taxa_mdr_credito_av_estimada),
                'credito_parcelado_mdr': float(self.taxa_mdr_credito_parcelado_estimada)
            }
        }


# ==============================================================================
# ADQUIRENTE_TEMPLATE - Templates para parsear CSVs (Ajuste #11)
# ==============================================================================

class AdquirenteTemplate(Base):
    """
    Template configurável para parsear arquivos de diferentes adquirentes.
    
    Ajuste #11: Cada operadora tem formato diferente - parser deve ser configurável.
    Suporta: Stone, Cielo, Rede, Getnet, SafraPay, PagSeguro, Mercado Pago, etc.
    
    ⚠️ IMPORTANTE: Não herda de BaseTenantModel para evitar conflito created_at/criado_em.
    """
    __tablename__ = "adquirentes_templates"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Identificação
    nome = Column(String(100), nullable=False, comment="Stone, Cielo, Rede, Getnet, etc")
    tipo_arquivo = Column(String(50), nullable=False, comment="recebimentos, pagamentos, vendas")
    ativo = Column(Boolean, default=True)
    
    # Configuração do parser
    separador = Column(String(5), default=';', nullable=False)
    encoding = Column(String(20), default='utf-8', nullable=False)
    tem_header = Column(Boolean, default=True)
    pular_linhas = Column(Integer, default=0, comment="Pular N linhas iniciais")
    
    # Mapeamento de colunas (JSONB flexível)
    mapeamento = Column(JSONB, nullable=False, comment="Mapeamento nome_campo: nome_coluna_csv")
    
    # Transformações opcionais (formato de datas, decimais, etc)
    transformacoes = Column(JSONB, nullable=True, comment="Regras de transformação por campo")
    
    # Auditoria
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    criado_por_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    importacoes = relationship("ConciliacaoImportacao", back_populates="template")
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'tipo_arquivo': self.tipo_arquivo,
            'ativo': self.ativo,
            'configuracao': {
                'separador': self.separador,
                'encoding': self.encoding,
                'tem_header': self.tem_header,
                'pular_linhas': self.pular_linhas
            },
            'mapeamento': self.mapeamento,
            'transformacoes': self.transformacoes
        }


# ==============================================================================
# ARQUIVO_EVIDENCIA - Armazena metadados dos arquivos (Ajuste #6)
# ==============================================================================

class ArquivoEvidencia(Base):
    """
    Metadados dos arquivos importados.
    
    Ajuste #6: Nunca apagar informações importadas - arquivos são evidências.
    Necessário para: auditoria, conferência futura, reprocessamento, rastreabilidade.
    
    ⚠️ IMPORTANTE: Este modelo NÃO herda de BaseTenantModel para evitar conflito
    de colunas (criado_em vs created_at). Gerencia tenant_id manualmente.
    """
    __tablename__ = "arquivos_evidencia"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Identificação
    nome_original = Column(String(255), nullable=False)
    tipo_arquivo = Column(String(50), nullable=False, comment="ofx, recebimentos, pagamentos, vendas")
    adquirente = Column(String(100), nullable=True, comment="Stone, Cielo, etc")
    
    # Armazenamento
    caminho_storage = Column(String(500), nullable=False, comment="Caminho no storage/S3")
    tamanho_bytes = Column(BigInteger, nullable=True)
    hash_md5 = Column(String(32), nullable=False, index=True, comment="Detectar duplicatas")
    hash_sha256 = Column(String(64), nullable=True, comment="Segurança adicional")
    
    # Metadados do conteúdo
    periodo_inicio = Column(Date, nullable=True, index=True)
    periodo_fim = Column(Date, nullable=True, index=True)
    total_linhas = Column(Integer, nullable=True)
    total_registros_processados = Column(Integer, nullable=True)
    
    # Auditoria (Ajuste #8)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    criado_por_id = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    
    # Relationships
    importacoes = relationship("ConciliacaoImportacao", back_populates="arquivo")
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome_original': self.nome_original,
            'tipo_arquivo': self.tipo_arquivo,
            'adquirente': self.adquirente,
            'tamanho_mb': round(self.tamanho_bytes / 1024 / 1024, 2) if self.tamanho_bytes else None,
            'hash_md5': self.hash_md5,
            'periodo': {
                'inicio': self.periodo_inicio.isoformat() if self.periodo_inicio else None,
                'fim': self.periodo_fim.isoformat() if self.periodo_fim else None
            },
            'total_linhas': self.total_linhas,
            'total_processados': self.total_registros_processados,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por_id': self.criado_por_id
        }


# ==============================================================================
# CONCILIACAO_IMPORTACAO - Dados brutos importados (Ajuste #2 - Separação)
# ==============================================================================

class ConciliacaoImportacao(Base):
    """
    Dados brutos importados (OFX, CSVs).
    
    Ajuste #2: Importação ≠ Processamento.
    Esta tabela apenas ARMAZENA dados, NÃO altera financeiro.
    
    ⚠️ IMPORTANTE: Não herda de BaseTenantModel para evitar conflito created_at/criado_em.
    """
    __tablename__ = "conciliacao_importacoes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Referências
    arquivo_evidencia_id = Column(Integer, ForeignKey('arquivos_evidencia.id', ondelete='RESTRICT'), nullable=False)
    adquirente_template_id = Column(Integer, ForeignKey('adquirentes_templates.id', ondelete='RESTRICT'), nullable=True)
    
    # Tipo de importação
    tipo_importacao = Column(
        String(50),
        nullable=False,
        index=True,
        comment="ofx_creditos, pagamentos_lotes, recebimentos_detalhados"
    )
    data_referencia = Column(Date, nullable=False, index=True, comment="Data do movimento/crédito")
    
    # Dados agregados
    total_registros = Column(Integer, default=0)
    total_valor = Column(Numeric(15, 2), default=0)
    status_importacao = Column(
        String(50),
        default='pendente',
        index=True,
        comment="pendente, processada, erro, cancelada"
    )
    
    # Resumo flexível (JSONB)
    resumo = Column(JSONB, nullable=True, comment="Resumo da importação (formato livre)")
    
    # Auditoria
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    criado_por_id = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    
    # Relationships
    arquivo = relationship("ArquivoEvidencia", back_populates="importacoes")
    template = relationship("AdquirenteTemplate", back_populates="importacoes")
    validacoes_ofx = relationship("ConciliacaoValidacao", foreign_keys="ConciliacaoValidacao.importacao_ofx_id", back_populates="importacao_ofx")
    validacoes_pagamentos = relationship("ConciliacaoValidacao", foreign_keys="ConciliacaoValidacao.importacao_pagamentos_id", back_populates="importacao_pagamentos")
    validacoes_recebimentos = relationship("ConciliacaoValidacao", foreign_keys="ConciliacaoValidacao.importacao_recebimentos_id", back_populates="importacao_recebimentos")
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo_importacao': self.tipo_importacao,
            'data_referencia': self.data_referencia.isoformat() if self.data_referencia else None,
            'total_registros': self.total_registros,
            'total_valor': float(self.total_valor) if self.total_valor else 0,
            'status': self.status_importacao,
            'resumo': self.resumo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }


# ==============================================================================
# CONCILIACAO_LOTE - Lotes de pagamento (Ajuste #3 - Estados)
# ==============================================================================

class ConciliacaoLote(BaseTenantModel):
    """
    Lotes de pagamento/transferências agrupadas.
    
    Ajuste #3: Sistema orientado a STATUS.
    Estados: previsto → informado → creditado → divergente
    """
    __tablename__ = "conciliacao_lotes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Vínculos
    importacao_pagamentos_id = Column(Integer, ForeignKey('conciliacao_importacoes.id', ondelete='SET NULL'), nullable=True)
    importacao_ofx_id = Column(Integer, ForeignKey('conciliacao_importacoes.id', ondelete='SET NULL'), nullable=True)
    movimentacao_bancaria_id = Column(Integer, ForeignKey('movimentacoes_bancarias.id', ondelete='SET NULL'), nullable=True)
    
    # Identificação
    adquirente = Column(String(100), nullable=False, index=True)
    identificador_lote = Column(String(255), nullable=True, comment="ID fornecido pela operadora (se existir)")
    data_pagamento = Column(Date, nullable=False, index=True)
    
    # Valores
    valor_bruto = Column(Numeric(15, 2), nullable=False)
    valor_liquido = Column(Numeric(15, 2), nullable=False)
    valor_descontos = Column(Numeric(15, 2), default=0)
    
    # Classificação
    bandeira = Column(String(50), nullable=True, comment="Visa, Master, Elo")
    modalidade = Column(String(50), nullable=True, comment="Antecipação, Débito, Crédito")
    
    # Status (Ajuste #3)
    status_lote = Column(
        String(50),
        default='previsto',
        index=True,
        comment="previsto, informado, creditado, divergente"
    )
    
    # Quantidade de parcelas
    quantidade_parcelas = Column(Integer, default=0, comment="ContaReceber vinculadas")
    
    # Auditoria
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # parcelas = relationship("ContaReceber", back_populates="lote")  # TEMPORARIAMENTE COMENTADO - ContaReceber não tem back_populates
    
    def to_dict(self):
        return {
            'id': self.id,
            'adquirente': self.adquirente,
            'data_pagamento': self.data_pagamento.isoformat() if self.data_pagamento else None,
            'valores': {
                'bruto': float(self.valor_bruto),
                'liquido': float(self.valor_liquido),
                'descontos': float(self.valor_descontos)
            },
            'bandeira': self.bandeira,
            'modalidade': self.modalidade,
            'status': self.status_lote,
            'quantidade_parcelas': self.quantidade_parcelas
        }


# ==============================================================================
# CONCILIACAO_VALIDACAO - Validação em cascata (Ajuste #4, #12)
# ==============================================================================

class ConciliacaoValidacao(BaseTenantModel):
    """
    Resultado da validação em cascata (OFX → Pagamentos → Recebimentos).
    
    Ajuste #4: Confiança BAIXA não bloqueia - apenas exige confirmação.
    Ajuste #12: Validar totais antes de liquidar.
    """
    __tablename__ = "conciliacao_validacoes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Referências
    importacao_ofx_id = Column(Integer, ForeignKey('conciliacao_importacoes.id', ondelete='CASCADE'), nullable=True)
    importacao_pagamentos_id = Column(Integer, ForeignKey('conciliacao_importacoes.id', ondelete='CASCADE'), nullable=True)
    importacao_recebimentos_id = Column(Integer, ForeignKey('conciliacao_importacoes.id', ondelete='CASCADE'), nullable=True)
    
    # Identificação
    data_referencia = Column(Date, nullable=False, index=True)
    adquirente = Column(String(100), nullable=False)
    
    # Totais validados
    total_ofx = Column(Numeric(15, 2), nullable=True)
    total_pagamentos = Column(Numeric(15, 2), nullable=True)
    total_recebimentos = Column(Numeric(15, 2), nullable=True)
    
    # Diferenças
    diferenca_ofx_pagamentos = Column(Numeric(15, 2), default=0)
    diferenca_pagamentos_recebimentos = Column(Numeric(15, 2), default=0)
    percentual_divergencia = Column(Numeric(5, 2), default=0)
    
    # Classificação (Ajuste #4 - nunca bloquear)
    confianca = Column(String(20), nullable=False, index=True, comment="ALTA, MEDIA, BAIXA")
    pode_processar = Column(Boolean, default=True, comment="Sempre True - sistema nunca bloqueia")
    requer_confirmacao = Column(Boolean, default=False)
    
    # Status
    status_validacao = Column(
        String(50),
        default='pendente',
        index=True,
        comment="pendente, parcial, concluida, divergente"
    )
    
    # Alertas (JSONB array)
    alertas = Column(JSONB, nullable=True, comment="Lista de alertas gerados")
    
    # Quantidades
    quantidade_parcelas = Column(Integer, default=0)
    quantidade_lotes = Column(Integer, default=0)
    parcelas_confirmadas = Column(Integer, default=0)
    parcelas_orfas = Column(Integer, default=0)
    
    # Auditoria
    criado_em = Column(DateTime, default=datetime.utcnow)
    criado_por_id = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    
    # Relationships
    importacao_ofx = relationship("ConciliacaoImportacao", foreign_keys=[importacao_ofx_id], back_populates="validacoes_ofx")
    importacao_pagamentos = relationship("ConciliacaoImportacao", foreign_keys=[importacao_pagamentos_id], back_populates="validacoes_pagamentos")
    importacao_recebimentos = relationship("ConciliacaoImportacao", foreign_keys=[importacao_recebimentos_id], back_populates="validacoes_recebimentos")
    logs = relationship("ConciliacaoLog", back_populates="validacao")
    
    def to_dict(self):
        return {
            'id': self.id,
            'data_referencia': self.data_referencia.isoformat() if self.data_referencia else None,
            'adquirente': self.adquirente,
            'totais': {
                'ofx': float(self.total_ofx) if self.total_ofx else None,
                'pagamentos': float(self.total_pagamentos) if self.total_pagamentos else None,
                'recebimentos': float(self.total_recebimentos) if self.total_recebimentos else None
            },
            'diferencas': {
                'ofx_vs_pagamentos': float(self.diferenca_ofx_pagamentos),
                'pagamentos_vs_recebimentos': float(self.diferenca_pagamentos_recebimentos),
                'percentual': float(self.percentual_divergencia)
            },
            'confianca': self.confianca,
            'pode_processar': self.pode_processar,
            'requer_confirmacao': self.requer_confirmacao,
            'status': self.status_validacao,
            'alertas': self.alertas or [],
            'quantidades': {
                'parcelas': self.quantidade_parcelas,
                'lotes': self.quantidade_lotes,
                'confirmadas': self.parcelas_confirmadas,
                'orfas': self.parcelas_orfas
            }
        }


# ==============================================================================
# CONCILIACAO_LOG - Log completo de auditoria (Ajuste #7, #8)
# ==============================================================================

class ConciliacaoLog(BaseTenantModel):
    """
    Log completo de auditoria.
    
    Ajuste #7: Versionamento para rastrear reprocessamentos.
    Ajuste #8: Guardar log completo (data/hora, usuário, arquivos, quantidades, valores).
    """
    __tablename__ = "conciliacao_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Vínculo
    conciliacao_validacao_id = Column(Integer, ForeignKey('conciliacao_validacoes.id', ondelete='CASCADE'), nullable=True)
    
    # Versionamento (Ajuste #7)
    versao_conciliacao = Column(
        Integer,
        default=1,
        nullable=False,
        index=True,
        comment="Incrementa a cada reprocessamento"
    )
    
    # Ação
    acao = Column(
        String(100),
        nullable=False,
        index=True,
        comment="importar_ofx, processar_conciliacao, reverter_conciliacao, etc"
    )
    status_acao = Column(
        String(50),
        default='sucesso',
        comment="sucesso, erro, parcial, revertido"
    )
    
    # Detalhes (JSONB flexível)
    arquivos_utilizados = Column(JSONB, nullable=True, comment="Lista de arquivos usados")
    quantidades = Column(JSONB, nullable=True, comment="Quantidades processadas")
    diferencas = Column(JSONB, nullable=True, comment="Diferenças encontradas")
    
    # Motivo (para reversões ou decisões manuais)
    motivo = Column(Text, nullable=True, comment="Justificativa de reversão ou confirmação")
    
    # Auditoria completa (Ajuste #8)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    criado_por_id = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    ip_origem = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    # Relationships
    validacao = relationship("ConciliacaoValidacao", back_populates="logs")
    
    def to_dict(self):
        return {
            'id': self.id,
            'versao_conciliacao': self.versao_conciliacao,
            'acao': self.acao,
            'status': self.status_acao,
            'arquivos_utilizados': self.arquivos_utilizados,
            'quantidades': self.quantidades,
            'diferencas': self.diferencas,
            'motivo': self.motivo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por_id': self.criado_por_id,
            'ip_origem': self.ip_origem
        }


# ==============================================================================
# CONCILIACAO_RECEBIMENTOS - Dados da planilha Stone (Aba 2)
# ==============================================================================

class ConciliacaoRecebimento(BaseTenantModel):
    """
    Tabela para salvar dados dos recebimentos importados da planilha Stone.
    
    Usado na Aba 2 (Conciliação de Recebimentos) para validação em cascata:
    - Recebimentos Detalhados
    - Recibo de Lote
    - OFX
    
    E na Aba 3 (Amarração) para vincular recebimentos às vendas.
    """
    __tablename__ = "conciliacao_recebimentos"
    __table_args__ = {'extend_existing': True}
    
    # Sobrescrever id para usar autoincrement padrão (não Identity)
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Dados da planilha Stone
    nsu = Column(String(100), nullable=False, index=True, comment="NSU da transação")
    adquirente = Column(String(100), nullable=True, index=True, comment="Operadora do recebimento")
    data_recebimento = Column(Date, nullable=False, index=True, comment="Data que dinheiro entrou")
    valor = Column(Numeric(15, 2), nullable=False, comment="Valor do recebimento")
    parcela_numero = Column(Integer, nullable=True, comment="Número da parcela (1, 2, 3, etc)")
    total_parcelas = Column(Integer, nullable=True, comment="Total de parcelas da venda")
    
    # Tipo de recebimento
    tipo_recebimento = Column(
        String(30),
        nullable=False,
        default='parcela_individual',
        comment="antecipacao (todas de vez) | parcela_individual (1/3, 2/3, etc)"
    )
    
    # Lote (agrupamento Stone)
    lote_id = Column(String(100), nullable=True, index=True, comment="ID do lote Stone")
    lote_valor = Column(Numeric(15, 2), nullable=True, comment="Valor total do lote")
    
    # Validação (Aba 2)
    validado = Column(Boolean, default=False, nullable=False, index=True, comment="Se passou validação cascata (Aba 2)")
    validado_em = Column(DateTime, nullable=True, comment="Quando foi validado")
    validacao_id = Column(Integer, ForeignKey('conciliacao_validacoes.id'), nullable=True, comment="FK para validação")
    
    # Amarração (Aba 3)
    amarrado = Column(Boolean, default=False, nullable=False, index=True, comment="Se foi amarrado a uma venda (Aba 3)")
    amarrado_em = Column(DateTime, nullable=True, comment="Quando foi amarrado")
    venda_id = Column(Integer, ForeignKey('vendas.id'), nullable=True, index=True, comment="FK para venda vinculada")
    
    # Auditoria - Sobrescrever nomes para não conflitar com BaseTenantModel
    criado_em = Column('criado_em', DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column('atualizado_em', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Desabilitar created_at/updated_at do BaseTenantModel
    created_at = None
    updated_at = None
    
    # Relationships
    validacao = relationship("ConciliacaoValidacao", foreign_keys=[validacao_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': str(self.tenant_id),
            'nsu': self.nsu,
            'adquirente': self.adquirente,
            'data_recebimento': self.data_recebimento.isoformat() if self.data_recebimento else None,
            'valor': float(self.valor) if self.valor else 0,
            'parcela_numero': self.parcela_numero,
            'total_parcelas': self.total_parcelas,
            'tipo_recebimento': self.tipo_recebimento,
            'lote_id': self.lote_id,
            'lote_valor': float(self.lote_valor) if self.lote_valor else 0,
            'validado': self.validado,
            'amarrado': self.amarrado,
            'venda_id': self.venda_id
        }


# ==============================================================================
# CONCILIACAO_METRICAS - KPIs de saúde do sistema
# ==============================================================================

class ConciliacaoMetrica(Base):
    """
    Tabela para armazenar métricas diárias de amarração automática.
    
    Usado para monitorar a saúde do sistema:
    - % de amarração automática
    - Se cair abaixo de 90% = alerta CRÍTICO (problema na operação)
    
    Permite gráficos históricos e alertas proativos.
    
    NOTA: Não herda de BaseTenantModel porque tem estrutura customizada (criado_em ao invés de created_at)
    """
    __tablename__ = "conciliacao_metricas"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Data da métrica
    data_referencia = Column(Date, nullable=False, index=True, comment="Data dos recebimentos processados")
    
    # Quantidades
    total_recebimentos = Column(Integer, nullable=False, default=0, comment="Total de recebimentos validados (Aba 2)")
    recebimentos_amarrados = Column(Integer, nullable=False, default=0, comment="Recebimentos amarrados automaticamente")
    recebimentos_orfaos = Column(Integer, nullable=False, default=0, comment="Recebimentos SEM venda correspondente")
    
    # Valores
    valor_total_recebimentos = Column(Numeric(15, 2), nullable=False, default=0, comment="Valor total dos recebimentos")
    valor_amarrado = Column(Numeric(15, 2), nullable=False, default=0, comment="Valor amarrado automaticamente")
    valor_orfao = Column(Numeric(15, 2), nullable=False, default=0, comment="Valor órfão (sem venda)")
    
    # KPI principal
    taxa_amarracao_automatica = Column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        index=True,
        comment="% de amarração automática (98% = saudável, < 90% = CRÍTICO)"
    )
    
    # Alertas
    alerta_saude = Column(
        String(20),
        nullable=False,
        default='OK',
        index=True,
        comment="OK (>= 90%) | CRÍTICO (< 90%)"
    )
    
    # Parcelas liquidadas (transparência)
    parcelas_liquidadas = Column(Integer, nullable=False, default=0, comment="Quantas parcelas foram baixadas")
    valor_total_liquidado = Column(Numeric(15, 2), nullable=False, default=0, comment="Valor total liquidado")
    
    # Auditoria
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    criado_por_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="Quem processou Aba 3")
    
    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': str(self.tenant_id),
            'data_referencia': self.data_referencia.isoformat() if self.data_referencia else None,
            'quantidades': {
                'total_recebimentos': self.total_recebimentos,
                'amarrados': self.recebimentos_amarrados,
                'orfaos': self.recebimentos_orfaos
            },
            'valores': {
                'total': float(self.valor_total_recebimentos) if self.valor_total_recebimentos else 0,
                'amarrado': float(self.valor_amarrado) if self.valor_amarrado else 0,
                'orfao': float(self.valor_orfao) if self.valor_orfao else 0
            },
            'kpi': {
                'taxa_amarracao': float(self.taxa_amarracao_automatica) if self.taxa_amarracao_automatica else 0,
                'alerta_saude': self.alerta_saude
            },
            'liquidacao': {
                'parcelas': self.parcelas_liquidadas,
                'valor_total': float(self.valor_total_liquidado) if self.valor_total_liquidado else 0
            },
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }


# ==============================================================================
# HISTORICO_CONCILIACAO - Registro de Conciliações Realizadas
# ==============================================================================

class HistoricoConciliacao(BaseTenantModel):
    """
    Registro histórico de conciliações realizadas.
    
    Objetivo:
    - Rastrear quais datas/operadoras já foram conciliadas
    - Evitar reprocessamento duplicado
    - Auditoria completa do processo
    - Histórico consultável
    
    Cada registro = 1 conciliação completa (3 abas)
    """
    __tablename__ = "historico_conciliacao"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Identificação única da conciliação
    data_referencia = Column(
        Date,
        nullable=False,
        index=True,
        comment="Data conciliada (ex: 10/02/2026)"
    )
    operadora = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Operadora: Stone, PagSeguro, Rede, Cielo, etc."
    )
    
    # Status do processo
    status = Column(
        String(50),
        nullable=False,
        default='em_andamento',
        comment="em_andamento | concluida | reprocessada | cancelada"
    )
    
    # Abas concluídas
    aba1_concluida = Column(Boolean, default=False, comment="Conciliação de Vendas")
    aba2_concluida = Column(Boolean, default=False, comment="Validação de Recebimentos")
    aba3_concluida = Column(Boolean, default=False, comment="Amarração Automática")
    
    aba1_concluida_em = Column(DateTime, nullable=True)
    aba2_concluida_em = Column(DateTime, nullable=True)
    aba3_concluida_em = Column(DateTime, nullable=True)
    
    # Metadados da conciliação
    arquivos_processados = Column(
        JSONB,
        comment="Lista de arquivos: [{nome, tipo, tamanho, hash}]"
    )
    
    totais = Column(
        JSONB,
        comment="Valores totais: {vendas, recebimentos, amarrado, divergencias}"
    )
    
    divergencias_encontradas = Column(Integer, default=0)
    divergencias_aceitas = Column(Boolean, default=False)
    
    # Resultado da amarração (Aba 3)
    parcelas_amarradas = Column(Integer, default=0)
    parcelas_orfas = Column(Integer, default=0)
    taxa_amarracao = Column(Numeric(5, 2), comment="% de sucesso da amarração")
    
    # Auditoria
    usuario_responsavel = Column(String(200), comment="Usuário que realizou")
    observacoes = Column(Text, nullable=True)
    
    # Concluída em (quando todas as 3 abas terminarem)
    concluida_em = Column(DateTime, nullable=True)
    
    # Índice composto para evitar duplicação
    __table_args__ = (
        {'extend_existing': True},
    )
    
    def __repr__(self):
        return f"<HistoricoConciliacao(data={self.data_referencia}, operadora={self.operadora}, status={self.status})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': str(self.tenant_id),
            'data_referencia': self.data_referencia.isoformat() if self.data_referencia else None,
            'operadora': self.operadora,
            'status': self.status,
            'abas': {
                'aba1': {
                    'concluida': self.aba1_concluida,
                    'concluida_em': self.aba1_concluida_em.isoformat() if self.aba1_concluida_em else None
                },
                'aba2': {
                    'concluida': self.aba2_concluida,
                    'concluida_em': self.aba2_concluida_em.isoformat() if self.aba2_concluida_em else None
                },
                'aba3': {
                    'concluida': self.aba3_concluida,
                    'concluida_em': self.aba3_concluida_em.isoformat() if self.aba3_concluida_em else None
                }
            },
            'arquivos': self.arquivos_processados or [],
            'totais': self.totais or {},
            'divergencias': {
                'encontradas': self.divergencias_encontradas,
                'aceitas': self.divergencias_aceitas
            },
            'amarracao': {
                'parcelas_amarradas': self.parcelas_amarradas,
                'parcelas_orfas': self.parcelas_orfas,
                'taxa': float(self.taxa_amarracao) if self.taxa_amarracao else 0
            },
            'usuario_responsavel': self.usuario_responsavel,
            'observacoes': self.observacoes,
            'concluida_em': self.concluida_em.isoformat() if self.concluida_em else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
