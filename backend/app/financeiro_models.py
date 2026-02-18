"""
Models para o Módulo Financeiro
Contas a Pagar, Contas a Receber, Categorias, Formas de Pagamento
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base
from .base_models import BaseTenantModel
from app.utils.serialization import safe_decimal_to_float, safe_datetime_to_iso


class CategoriaFinanceira(BaseTenantModel):
    """Categorias para organizar receitas e despesas"""
    __tablename__ = "categorias_financeiras"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(String(20), nullable=False)  # 'receita' ou 'despesa'
    cor = Column(String(7))
    icone = Column(String(50))
    descricao = Column(Text)
    categoria_pai_id = Column(Integer, ForeignKey('categorias_financeiras.id'))
    ativo = Column(Boolean, default=True)
    
    # ============================
    # VINCULO COM DRE (NOVO)
    # ============================
    dre_subcategoria_id = Column(
        Integer,
        ForeignKey("dre_subcategorias.id"),
        nullable=True
    )
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    categoria_pai = relationship("CategoriaFinanceira", remote_side=[id], backref="subcategorias")
    contas_pagar = relationship("ContaPagar", back_populates="categoria")
    contas_receber = relationship("ContaReceber", back_populates="categoria")


class FormaPagamento(BaseTenantModel):
    """Formas de pagamento disponíveis"""
    __tablename__ = "formas_pagamento"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(String(20), nullable=False)  # 'dinheiro', 'cartao_credito', 'cartao_debito', 'pix', 'boleto', 'transferencia'
    
    # Taxas e prazos (FASE 1 - novos)
    taxa_percentual = Column(Numeric(5, 2), default=0)
    taxa_fixa = Column(Numeric(10, 2), default=0)
    prazo_dias = Column(Integer, default=0)  # Prazo para recebimento
    prazo_recebimento = Column(Integer, default=0)  # dias (manter compatibilidade)
    
    # Configurações (FASE 1 - novos)
    operadora = Column(String(50))  # Stone, Cielo, Rede, etc
    gera_contas_receber = Column(Boolean, default=False)
    split_parcelas = Column(Boolean, default=False)
    conta_bancaria_destino_id = Column(Integer, ForeignKey('contas_bancarias.id'))
    requer_nsu = Column(Boolean, default=False)
    tipo_cartao = Column(String(20))  # debito, credito, voucher
    bandeira = Column(String(20))  # visa, master, elo, amex
    
    # Parcelamento
    ativo = Column(Boolean, default=True)
    permite_parcelamento = Column(Boolean, default=False)
    max_parcelas = Column(Integer, default=1)
    parcelas_maximas = Column(Integer, default=1)  # manter compatibilidade
    taxas_por_parcela = Column(Text)  # JSON com taxas específicas por número de parcelas
    
    # Operadora de Cartão (FK desabilitado - tabela operadoras_cartao não existe)
    operadora_id = Column(Integer, nullable=True, index=True)  # was: ForeignKey('operadoras_cartao.id')
    
    # Antecipação de recebíveis
    permite_antecipacao = Column(Boolean, default=False)
    dias_recebimento_antecipado = Column(Integer)  # Em quantos dias o dinheiro cai com antecipação
    taxa_antecipacao_percentual = Column(Numeric(5, 2))  # Taxa adicional para antecipação (opcional)
    
    # UI
    icone = Column(String(50))
    cor = Column(String(7))
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conta_bancaria_destino = relationship("ContaBancaria", foreign_keys=[conta_bancaria_destino_id])
    # operadora_cartao = relationship("OperadoraCartao", foreign_keys=[operadora_id])  # Disabled - tabela não existe
    contas_receber = relationship("ContaReceber", back_populates="forma_pagamento")
    pagamentos = relationship("Pagamento", back_populates="forma_pagamento")
    recebimentos = relationship("Recebimento", back_populates="forma_pagamento")


class ContaPagar(BaseTenantModel):
    """Contas a pagar (despesas)"""
    __tablename__ = "contas_pagar"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(255), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey('clientes.id'))
    categoria_id = Column(Integer, ForeignKey('categorias_financeiras.id'))  # UX/Agrupamento
    
    # ============================
    # VINCULO COM DRE (OBRIGATORIO)
    # ============================
    dre_subcategoria_id = Column(
        Integer,
        nullable=True,  # Opcional para compras sem classificação DRE ainda
        index=True,
        comment="Subcategoria DRE - fonte da verdade contábil"
    )
    canal = Column(
        String(50),
        nullable=True,  # Opcional para compras (não é venda)
        index=True,
        comment="Canal de venda: loja_fisica, mercado_livre, shopee, amazon"
    )
    
    # Valores
    valor_original = Column(Numeric(10, 2), nullable=False)
    valor_pago = Column(Numeric(10, 2), default=0)
    valor_desconto = Column(Numeric(10, 2), default=0)
    valor_juros = Column(Numeric(10, 2), default=0)
    valor_multa = Column(Numeric(10, 2), default=0)
    valor_final = Column(Numeric(10, 2), nullable=False)
    
    # Datas
    data_emissao = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=False, index=True)
    data_pagamento = Column(Date)
    
    # Status
    status = Column(String(20), default='pendente', index=True)  # 'pendente', 'pago', 'vencido', 'cancelado', 'parcial'
    
    # Parcelamento
    eh_parcelado = Column(Boolean, default=False)
    numero_parcela = Column(Integer)
    total_parcelas = Column(Integer)
    conta_principal_id = Column(Integer, ForeignKey('contas_pagar.id'))
    
    # Recorrência
    eh_recorrente = Column(Boolean, default=False)
    tipo_recorrencia = Column(String(20))  # 'semanal' (7 dias), 'quinzenal' (15 dias), 'mensal', 'personalizado'
    intervalo_dias = Column(Integer)  # Para recorrências personalizadas (ex: 10, 20, 45 dias)
    data_inicio_recorrencia = Column(Date)
    data_fim_recorrencia = Column(Date)  # Opcional: quando a recorrência deve parar
    numero_repeticoes = Column(Integer)  # Opcional: quantas vezes deve repetir
    proxima_recorrencia = Column(Date)
    conta_recorrencia_origem_id = Column(Integer, ForeignKey('contas_pagar.id'))  # ID da conta que originou esta
    
    # Referências
    nota_entrada_id = Column(Integer, ForeignKey('notas_entrada.id'), index=True)
    # lancamento_manual_id = Column(Integer, ForeignKey('lancamentos_manuais.id'), index=True)  # TEMPORARIAMENTE DESABILITADO
    nfe_numero = Column(String(50))
    documento = Column(String(100))
    observacoes = Column(Text)
    
    # Rateio Online vs Loja Física (para filtros e relatórios)
    percentual_online = Column(Float, default=0)  # % desta conta que é referente a vendas online
    percentual_loja = Column(Float, default=100)  # % desta conta que é referente a loja física
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
    categoria = relationship("CategoriaFinanceira", back_populates="contas_pagar")
    pagamentos = relationship("Pagamento", back_populates="conta", cascade="all, delete-orphan")
    parcelas = relationship("ContaPagar", backref="conta_principal", remote_side=[id], foreign_keys=[conta_principal_id])


class ContaReceber(BaseTenantModel):
    """Contas a receber (receitas)"""
    __tablename__ = "contas_receber"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(255), nullable=False)
    cliente_id = Column(Integer, ForeignKey('clientes.id'))
    categoria_id = Column(Integer, ForeignKey('categorias_financeiras.id'))  # UX/Agrupamento
    forma_pagamento_id = Column(Integer, ForeignKey('formas_pagamento.id'))
    
    # ============================
    # VINCULO COM DRE (OBRIGATORIO)
    # ============================
    dre_subcategoria_id = Column(
        Integer,
        nullable=False,
        index=True,
        comment="Subcategoria DRE - fonte da verdade contábil"
    )
    canal = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Canal de venda: loja_fisica, mercado_livre, shopee, amazon"
    )
    
    # Valores
    valor_original = Column(Numeric(10, 2), nullable=False)
    valor_recebido = Column(Numeric(10, 2), default=0)
    valor_desconto = Column(Numeric(10, 2), default=0)
    valor_juros = Column(Numeric(10, 2), default=0)
    valor_multa = Column(Numeric(10, 2), default=0)
    valor_final = Column(Numeric(10, 2), nullable=False)
    
    # Datas
    data_emissao = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=False, index=True)
    data_recebimento = Column(Date)
    
    # Status
    status = Column(String(20), default='pendente', index=True)  # 'pendente', 'recebido', 'vencido', 'cancelado', 'parcial'
    
    # Parcelamento
    eh_parcelado = Column(Boolean, default=False)
    numero_parcela = Column(Integer)
    total_parcelas = Column(Integer)
    conta_principal_id = Column(Integer, ForeignKey('contas_receber.id'))
    
    # Recorrência
    eh_recorrente = Column(Boolean, default=False)
    tipo_recorrencia = Column(String(20))  # 'semanal' (7 dias), 'quinzenal' (15 dias), 'mensal', 'personalizado'
    intervalo_dias = Column(Integer)  # Para recorrências personalizadas
    data_inicio_recorrencia = Column(Date)
    data_fim_recorrencia = Column(Date)
    numero_repeticoes = Column(Integer)
    proxima_recorrencia = Column(Date)
    conta_recorrencia_origem_id = Column(Integer, ForeignKey('contas_receber.id'))
    
    # Referências
    venda_id = Column(Integer, ForeignKey('vendas.id', ondelete='CASCADE'), index=True)
    # lancamento_manual_id = Column(Integer, ForeignKey('lancamentos_manuais.id'), index=True)  # TEMPORARIAMENTE DESABILITADO
    nfe_numero = Column(String(50))
    documento = Column(String(100))
    observacoes = Column(Text)
    
    # ============================
    # CONCILIAÇÃO DE CARTÃO (FASE 3)
    # ============================
    nsu = Column(String(100), nullable=True, index=True, comment="NSU da transação de cartão")
    adquirente = Column(String(50), nullable=True, comment="Adquirente (Stone, Cielo, etc)")
    conciliado = Column(Boolean, default=False, nullable=False, index=True, comment="Se a transação foi conciliada")
    data_conciliacao = Column(Date, nullable=True, comment="Data em que a conciliação foi realizada")
    
    # ============================
    # CONCILIAÇÃO COMPLETA (FASE 1+2) - Ajustes #1-#7
    # ============================
    # Status detalhado (Ajuste #1)
    status_conciliacao = Column(
        String(50), 
        default='prevista',
        index=True,
        comment="prevista|confirmada_operadora|aguardando_lote|em_lote|liquidada"
    )
    
    # Taxas estimadas (calculadas no PDV - Ajuste #9)
    taxa_mdr_estimada = Column(Numeric(5, 2), nullable=True, comment="MDR calculado no PDV")
    taxa_antecipacao_estimada = Column(Numeric(5, 2), nullable=True, comment="Taxa de antecipação calculada")
    
    # Taxas reais (importadas do arquivo da operadora)
    taxa_mdr_real = Column(Numeric(5, 2), nullable=True, comment="MDR real do arquivo operadora")
    taxa_antecipacao_real = Column(Numeric(5, 2), nullable=True, comment="Taxa real do arquivo")
    
    # Valores líquidos
    valor_liquido_estimado = Column(Numeric(15, 2), nullable=True, comment="Valor bruto - taxas estimadas")
    valor_liquido_real = Column(Numeric(15, 2), nullable=True, comment="Valor líquido do arquivo operadora")
    
    # Datas de vencimento
    data_vencimento_estimada = Column(Date, nullable=True, comment="Vencimento calculado (D+X)")
    data_vencimento_real = Column(Date, nullable=True, comment="Vencimento informado pela operadora")
    
    # ============================
    # AMARRAÇÃO VENDA ↔ RECEBIMENTO (NOVA ARQUITETURA 3 ABAS)
    # ============================
    tipo_recebimento = Column(
        String(30), 
        nullable=True, 
        comment="antecipacao (todas parcelas) | parcela_individual (1/3, 2/3, etc)"
    )
    # FK desabilitado - tabela conciliacao_recebimentos pode não estar registrada
    conciliacao_recebimento_id = Column(
        Integer, 
        # was: ForeignKey('conciliacao_recebimentos.id'),
        nullable=True,
        index=True,
        comment="FK para recebimento Stone (idempotência)"
    )
    
    # Divergências (para alertas - Ajuste #10)
    diferenca_taxa = Column(Numeric(5, 2), nullable=True, comment="MDR real - MDR estimado")
    diferenca_valor = Column(Numeric(15, 2), nullable=True, comment="Valor líquido real - estimado")
    
    # Vínculo com lotes (Ajuste #3) - FK desabilitado
    conciliacao_lote_id = Column(Integer, nullable=True)  # was: ForeignKey('conciliacao_lotes.id', ondelete='SET NULL')
    
    # Vínculo com validação (FK desabilitado - tabela conciliacao_validacoes não existe)
    validacao_id = Column(
        Integer, 
        # was: ForeignKey('conciliacao_validacoes.id', ondelete='SET NULL'), 
        nullable=True,
        index=True,
        comment="Validação que processou esta parcela (evita reprocessamento)"
    )
    
    # Versionamento (Ajuste #7)
    versao_conciliacao = Column(Integer, default=1, comment="Incrementa a cada reprocessamento")
    
    # Data de liquidação efetiva
    data_liquidacao = Column(Date, nullable=True, index=True, comment="Data em que o dinheiro entrou na conta")
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    categoria = relationship("CategoriaFinanceira", back_populates="contas_receber")
    forma_pagamento = relationship("FormaPagamento", back_populates="contas_receber")
    recebimentos = relationship("Recebimento", back_populates="conta", cascade="all, delete-orphan")
    parcelas = relationship("ContaReceber", backref="conta_principal", remote_side=[id], foreign_keys=[conta_principal_id])
    # lote = relationship("ConciliacaoLote", foreign_keys=[conciliacao_lote_id], back_populates="parcelas")  # TODO: Criar modelo ConciliacaoLote


class Pagamento(BaseTenantModel):
    """Registro de pagamentos (baixas de contas a pagar)"""
    __tablename__ = "pagamentos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    conta_pagar_id = Column(Integer, ForeignKey('contas_pagar.id'), nullable=False, index=True)
    forma_pagamento_id = Column(Integer, ForeignKey('formas_pagamento.id'))
    
    valor_pago = Column(Numeric(10, 2), nullable=False)
    data_pagamento = Column(Date, nullable=False, index=True)
    
    observacoes = Column(Text)
    comprovante = Column(String(255))
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conta = relationship("ContaPagar", back_populates="pagamentos")
    forma_pagamento = relationship("FormaPagamento", back_populates="pagamentos")


class Recebimento(BaseTenantModel):
    """Registro de recebimentos (baixas de contas a receber)"""
    __tablename__ = "recebimentos"
    __table_args__ = {'extend_existing': True}
    
    # Override BaseTenantModel's updated_at since this table doesn't have it
    updated_at = None
    
    id = Column(Integer, primary_key=True, index=True)
    conta_receber_id = Column(Integer, ForeignKey('contas_receber.id', ondelete='CASCADE'), nullable=False, index=True)
    forma_pagamento_id = Column(Integer, ForeignKey('formas_pagamento.id'))
    
    valor_recebido = Column(Numeric(10, 2), nullable=False)
    data_recebimento = Column(Date, nullable=False, index=True)
    
    observacoes = Column(Text)
    comprovante = Column(String(255))
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conta = relationship("ContaReceber", back_populates="recebimentos")
    forma_pagamento = relationship("FormaPagamento", back_populates="recebimentos")


# ============================================================================
# NOVAS CLASSES - FASE 1: Base Financeira
# ============================================================================

class ContaBancaria(BaseTenantModel):
    """Contas bancárias, caixas físicos e carteiras digitais"""
    __tablename__ = "contas_bancarias"
    __table_args__ = {'extend_existing': True}
    
    # id, tenant_id, created_at, updated_at já vêm de BaseTenantModel
    nome = Column(String(100), nullable=False)
    tipo = Column(String(20), nullable=False, index=True)  # corrente, poupanca, caixa_fisico, carteira_digital
    banco = Column(String(50))
    agencia = Column(String(10))
    conta = Column(String(20))
    saldo_inicial = Column(Numeric(15, 2), default=0)
    saldo_atual = Column(Numeric(15, 2), default=0)
    cor = Column(String(7), default='#3B82F6')
    icone = Column(String(50))
    instituicao_bancaria = Column(Boolean, default=False, index=True)  # Flag para identificar bancos reais
    ativa = Column(Boolean, default=True, index=True)
    observacoes = Column(Text)
    
    # Auditoria - quem criou a conta
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationships
    movimentacoes = relationship("MovimentacaoFinanceira", back_populates="conta_bancaria", cascade="all, delete-orphan")


class MovimentacaoFinanceira(BaseTenantModel):
    """Extrato unificado de todas as movimentações financeiras"""
    __tablename__ = "movimentacoes_financeiras"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    data_movimento = Column(DateTime, nullable=False, index=True)
    tipo = Column(String(20), nullable=False, index=True)  # entrada, saida, transferencia
    valor = Column(Numeric(15, 2), nullable=False)
    
    # Relacionamentos
    conta_bancaria_id = Column(Integer, ForeignKey('contas_bancarias.id'), nullable=False, index=True)
    categoria_id = Column(Integer, ForeignKey('categorias_financeiras.id'))
    forma_pagamento_id = Column(Integer, ForeignKey('formas_pagamento.id'))
    
    # Origem (de onde veio essa movimentação)
    origem_tipo = Column(String(30))  # venda, compra, nfe, despesa, transferencia, ajuste, conta_pagar, conta_receber
    origem_id = Column(Integer)
    origem_venda = Column(String(20))  # fisica, online
    
    # Status e metadados
    status = Column(String(20), default='realizado', index=True)  # previsto, realizado, cancelado
    documento = Column(String(100))
    descricao = Column(Text)
    observacoes = Column(Text)
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conta_bancaria = relationship("ContaBancaria", back_populates="movimentacoes")
    categoria = relationship("CategoriaFinanceira")
    forma_pagamento = relationship("FormaPagamento")


# ============================================================================
# LANÇAMENTOS MANUAIS E RECORRENTES (FLUXO DE CAIXA)
# ============================================================================

class LancamentoManual(BaseTenantModel):
    """Lançamentos manuais de débito/crédito no fluxo de caixa"""
    __tablename__ = "lancamentos_manuais"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Tipo
    tipo = Column(String(20), nullable=False, index=True)  # entrada, saida
    
    # Valores
    valor = Column(Numeric(10, 2), nullable=False)
    descricao = Column(String(255), nullable=False)
    
    # Datas
    data_lancamento = Column(Date, nullable=False, index=True)  # Data em que acontece
    data_competencia = Column(Date, nullable=True)  # Mês/ano de competência
    
    # Status
    status = Column(String(20), default='previsto', index=True)  # previsto, realizado, cancelado
    realizado_em = Column(DateTime, nullable=True)  # Quando foi realizado
    
    # Categorização
    categoria_id = Column(Integer, ForeignKey('categorias_financeiras.id'), nullable=True)
    conta_bancaria_id = Column(Integer, ForeignKey('contas_bancarias.id'), nullable=True)
    
    # Detalhes
    documento = Column(String(100), nullable=True)  # Nº documento, boleto, etc
    fornecedor_cliente = Column(String(255), nullable=True)  # Nome do fornecedor/cliente
    observacoes = Column(Text, nullable=True)
    
    # Recorrência (se veio de um lançamento recorrente)
    lancamento_recorrente_id = Column(Integer, ForeignKey('lancamentos_recorrentes.id'), nullable=True)
    
    # Flags para IA
    gerado_automaticamente = Column(Boolean, default=False)  # Se foi gerado por IA ou sistema
    confianca_ia = Column(Numeric(5, 2), nullable=True)  # % de confiança da IA (0-100)
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    categoria = relationship("CategoriaFinanceira")
    conta_bancaria = relationship("ContaBancaria")
    lancamento_recorrente = relationship("LancamentoRecorrente", back_populates="lancamentos_gerados")


class LancamentoRecorrente(BaseTenantModel):
    """Lançamentos recorrentes (água, luz, aluguel, etc) que geram lançamentos automáticos"""
    __tablename__ = "lancamentos_recorrentes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Tipo
    tipo = Column(String(20), nullable=False, index=True)  # entrada, saida
    
    # Valores
    valor_medio = Column(Numeric(10, 2), nullable=False)  # Valor médio/base
    descricao = Column(String(255), nullable=False)
    
    # Recorrência
    frequencia = Column(String(20), nullable=False)  # mensal, bimestral, trimestral, semestral, anual
    dia_vencimento = Column(Integer, nullable=False)  # Dia do mês (1-31)
    
    # Status
    ativo = Column(Boolean, default=True, index=True)
    data_inicio = Column(Date, nullable=False)  # A partir de quando gerar
    data_fim = Column(Date, nullable=True)  # Até quando gerar (null = infinito)
    
    # Categorização
    categoria_id = Column(Integer, ForeignKey('categorias_financeiras.id'), nullable=False)
    conta_bancaria_id = Column(Integer, ForeignKey('contas_bancarias.id'), nullable=True)
    
    # Detalhes
    fornecedor_cliente = Column(String(255), nullable=True)
    observacoes = Column(Text, nullable=True)
    
    # Controle de geração
    ultimo_mes_gerado = Column(String(7), nullable=True)  # YYYY-MM do último mês gerado
    gerar_com_antecedencia_dias = Column(Integer, default=5)  # Gerar X dias antes
    
    # Flags para IA
    permite_ajuste_ia = Column(Boolean, default=True)  # Se IA pode ajustar valor baseado em histórico
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    categoria = relationship("CategoriaFinanceira")
    conta_bancaria = relationship("ContaBancaria")
    lancamentos_gerados = relationship("LancamentoManual", back_populates="lancamento_recorrente")


# ============================================================================
# MODELS DE CONCILIAÇÃO BANCÁRIA
# ============================================================================

class ExtratoBancario(BaseTenantModel):
    """Extratos bancários importados (OFX, CSV, planilhas adquirentes)"""
    __tablename__ = "extratos_bancarios"
    __table_args__ = {'extend_existing': True}
    
    # id, tenant_id, created_at, updated_at são definidos por BaseTenantModel
    conta_bancaria_id = Column(Integer, ForeignKey('contas_bancarias.id', ondelete='CASCADE'), nullable=False)
    arquivo_nome = Column(String(255))
    data_upload = Column(DateTime, default=datetime.utcnow)
    periodo_inicio = Column(Date)
    periodo_fim = Column(Date)
    total_movimentacoes = Column(Integer, default=0)
    conciliadas = Column(Integer, default=0)
    pendentes = Column(Integer, default=0)
    status = Column(String(50))  # 'processando', 'concluido', 'revisao'
    
    # Relationships
    conta_bancaria = relationship("ContaBancaria")
    movimentacoes = relationship("MovimentacaoBancaria", back_populates="extrato")


class MovimentacaoBancaria(BaseTenantModel):
    """Cada linha do extrato bancário - núcleo da conciliação"""
    __tablename__ = "movimentacoes_bancarias"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    extrato_id = Column(Integer, ForeignKey('extratos_bancarios.id', ondelete='CASCADE'))
    conta_bancaria_id = Column(Integer, ForeignKey('contas_bancarias.id', ondelete='CASCADE'), nullable=False)
    
    # Dados do OFX
    fitid = Column(String(255))  # ID único do banco
    data_movimento = Column(DateTime)
    valor = Column(Numeric(15, 2))
    tipo = Column(String(20))  # 'CREDIT', 'DEBIT'
    memo = Column(Text)  # Descrição original
    
    # Classificação
    status_conciliacao = Column(String(50))  # 'pendente', 'sugerido', 'conciliado', 'manual'
    confianca_sugestao = Column(Integer)  # 0-100%
    
    # Vínculos
    tipo_vinculo = Column(String(50))  # 'fornecedor', 'transferencia', 'taxa', 'recebimento'
    fornecedor_id = Column(Integer, ForeignKey('clientes.id'))
    conta_pagar_id = Column(Integer, ForeignKey('contas_pagar.id', ondelete='SET NULL'))
    conta_receber_id = Column(Integer, ForeignKey('contas_receber.id', ondelete='SET NULL'))
    transferencia_destino_conta_id = Column(Integer, ForeignKey('contas_bancarias.id'))
    categoria_dre_id = Column(Integer, ForeignKey('dre_subcategorias.id'))
    centro_custo_id = Column(Integer)  # Futuro
    
    # Recorrência
    recorrente = Column(Boolean, default=False)
    periodicidade = Column(String(20))  # 'mensal', 'anual', etc
    grupo_recorrencia = Column(String(36))  # UUID para agrupar
    
    # Auditoria
    classificado_por = Column(Integer, ForeignKey('users.id'))
    classificado_em = Column(DateTime)
    regra_aplicada_id = Column(Integer, ForeignKey('regras_conciliacao.id'))
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    extrato = relationship("ExtratoBancario", back_populates="movimentacoes")
    conta_bancaria = relationship("ContaBancaria", foreign_keys=[conta_bancaria_id])
    conta_pagar = relationship("ContaPagar")
    conta_receber = relationship("ContaReceber")
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
    transferencia_destino = relationship("ContaBancaria", foreign_keys=[transferencia_destino_conta_id])
    regra_aplicada = relationship("RegraConciliacao")


class RegraConciliacao(BaseTenantModel):
    """Regras de aprendizado para classificação automática"""
    __tablename__ = "regras_conciliacao"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Padrão de reconhecimento
    padrao_memo = Column(String(255))  # Ex: "%MANFRIM%"
    tipo_operacao = Column(String(50))  # 'Pagamento', 'Pix', 'Taxa'
    descricao = Column(String(255))
    
    # Ação automática
    fornecedor_id = Column(Integer, ForeignKey('clientes.id'))
    categoria_dre_id = Column(Integer, ForeignKey('dre_subcategorias.id'))
    centro_custo_id = Column(Integer)
    
    # Confiabilidade
    vezes_aplicada = Column(Integer, default=0)
    vezes_confirmada = Column(Integer, default=0)
    confianca = Column(Integer)  # (confirmada/aplicada) * 100
    prioridade = Column(Integer)
    
    # Status
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
    categoria_dre = relationship("DRESubcategoria", foreign_keys=[categoria_dre_id])


class ProvisaoAutomatica(BaseTenantModel):
    """Provisões geradas automaticamente para contas recorrentes"""
    __tablename__ = "provisoes_automaticas"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    regra_id = Column(Integer, ForeignKey('regras_conciliacao.id'))
    conta_pagar_id = Column(Integer, ForeignKey('contas_pagar.id'))  # Provisão criada
    data_vencimento = Column(Date)
    valor = Column(Numeric(15, 2))
    descricao = Column(Text)
    status = Column(String(50))  # 'provisionado', 'realizado', 'cancelado'
    movimentacao_real_id = Column(Integer, ForeignKey('movimentacoes_bancarias.id', ondelete='SET NULL'))
    
    # Auditoria
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    regra = relationship("RegraConciliacao")
    conta_pagar = relationship("ContaPagar")
    movimentacao_real = relationship("MovimentacaoBancaria")


class TemplateAdquirente(BaseTenantModel):
    """Templates para importar planilhas de diferentes adquirentes"""
    __tablename__ = "templates_adquirentes"
    __table_args__ = {'extend_existing': True}
    
    # id, tenant_id, created_at, updated_at são definidos por BaseTenantModel
    nome_adquirente = Column(String(100))  # 'Stone', 'Cielo', 'Rede', etc
    tipo_relatorio = Column(String(50))  # 'vendas', 'recebimentos', 'extrato'
    mapeamento = Column(Text)  # JSON com mapeamento de colunas
    palavras_chave = Column(Text)  # JSON array com palavras para detecção
    colunas_obrigatorias = Column(Text)  # JSON array
    vezes_usado = Column(Integer, default=0)
    ultima_utilizacao = Column(DateTime)
    auto_aplicar = Column(Boolean, default=True)

