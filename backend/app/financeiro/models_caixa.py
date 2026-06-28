"""Bank account, cashflow, and recurring entry models for finance."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class ContaBancaria(BaseTenantModel):
    """Contas bancárias, caixas físicos e carteiras digitais"""

    __tablename__ = "contas_bancarias"
    __table_args__ = {"extend_existing": True}

    # id, tenant_id, created_at, updated_at já vêm de BaseTenantModel
    nome = Column(String(100), nullable=False)
    tipo = Column(
        String(20), nullable=False, index=True
    )  # corrente, poupanca, caixa_fisico, carteira_digital
    banco = Column(String(50))
    agencia = Column(String(10))
    conta = Column(String(20))
    saldo_inicial = Column(Numeric(15, 2), default=0)
    saldo_atual = Column(Numeric(15, 2), default=0)
    cor = Column(String(7), default="#3B82F6")
    icone = Column(String(50))
    instituicao_bancaria = Column(
        Boolean, default=False, index=True
    )  # Flag para identificar bancos reais
    ativa = Column(Boolean, default=True, index=True)
    observacoes = Column(Text)

    # Auditoria - quem criou a conta
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    movimentacoes = relationship(
        "MovimentacaoFinanceira",
        back_populates="conta_bancaria",
        cascade="all, delete-orphan",
    )


class MovimentacaoFinanceira(BaseTenantModel):
    """Extrato unificado de todas as movimentações financeiras"""

    __tablename__ = "movimentacoes_financeiras"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    data_movimento = Column(DateTime, nullable=False, index=True)
    tipo = Column(
        String(20), nullable=False, index=True
    )  # entrada, saida, transferencia
    valor = Column(Numeric(15, 2), nullable=False)

    # Relacionamentos
    conta_bancaria_id = Column(
        Integer, ForeignKey("contas_bancarias.id"), nullable=False, index=True
    )
    categoria_id = Column(Integer, ForeignKey("categorias_financeiras.id"))
    forma_pagamento_id = Column(Integer, ForeignKey("formas_pagamento.id"))

    # Origem (de onde veio essa movimentação)
    origem_tipo = Column(
        String(30)
    )  # venda, compra, nfe, despesa, transferencia, ajuste, conta_pagar, conta_receber
    origem_id = Column(Integer)
    origem_venda = Column(String(20))  # fisica, online

    # Status e metadados
    status = Column(
        String(20), default="realizado", index=True
    )  # previsto, realizado, cancelado
    documento = Column(String(100))
    descricao = Column(Text)
    observacoes = Column(Text)

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
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
    __table_args__ = {"extend_existing": True}

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
    status = Column(
        String(20), default="previsto", index=True
    )  # previsto, realizado, cancelado
    realizado_em = Column(DateTime, nullable=True)  # Quando foi realizado

    # Categorização
    categoria_id = Column(
        Integer, ForeignKey("categorias_financeiras.id"), nullable=True
    )
    conta_bancaria_id = Column(
        Integer, ForeignKey("contas_bancarias.id"), nullable=True
    )

    # Detalhes
    documento = Column(String(100), nullable=True)  # Nº documento, boleto, etc
    fornecedor_cliente = Column(
        String(255), nullable=True
    )  # Nome do fornecedor/cliente
    observacoes = Column(Text, nullable=True)

    # Recorrência (se veio de um lançamento recorrente)
    lancamento_recorrente_id = Column(
        Integer, ForeignKey("lancamentos_recorrentes.id"), nullable=True
    )

    # Flags para IA
    gerado_automaticamente = Column(
        Boolean, default=False
    )  # Se foi gerado por IA ou sistema
    confianca_ia = Column(Numeric(5, 2), nullable=True)  # % de confiança da IA (0-100)

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    categoria = relationship("CategoriaFinanceira")
    conta_bancaria = relationship("ContaBancaria")
    lancamento_recorrente = relationship(
        "LancamentoRecorrente", back_populates="lancamentos_gerados"
    )


class LancamentoRecorrente(BaseTenantModel):
    """Lançamentos recorrentes (água, luz, aluguel, etc) que geram lançamentos automáticos"""

    __tablename__ = "lancamentos_recorrentes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)

    # Tipo
    tipo = Column(String(20), nullable=False, index=True)  # entrada, saida

    # Valores
    valor_medio = Column(Numeric(10, 2), nullable=False)  # Valor médio/base
    descricao = Column(String(255), nullable=False)

    # Recorrência
    frequencia = Column(
        String(20), nullable=False
    )  # mensal, bimestral, trimestral, semestral, anual
    dia_vencimento = Column(Integer, nullable=False)  # Dia do mês (1-31)

    # Status
    ativo = Column(Boolean, default=True, index=True)
    data_inicio = Column(Date, nullable=False)  # A partir de quando gerar
    data_fim = Column(Date, nullable=True)  # Até quando gerar (null = infinito)

    # Categorização
    categoria_id = Column(
        Integer, ForeignKey("categorias_financeiras.id"), nullable=False
    )
    conta_bancaria_id = Column(
        Integer, ForeignKey("contas_bancarias.id"), nullable=True
    )

    # Detalhes
    fornecedor_cliente = Column(String(255), nullable=True)
    observacoes = Column(Text, nullable=True)

    # Controle de geração
    ultimo_mes_gerado = Column(String(7), nullable=True)  # YYYY-MM do último mês gerado
    gerar_com_antecedencia_dias = Column(Integer, default=5)  # Gerar X dias antes

    # Flags para IA
    permite_ajuste_ia = Column(
        Boolean, default=True
    )  # Se IA pode ajustar valor baseado em histórico

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    categoria = relationship("CategoriaFinanceira")
    conta_bancaria = relationship("ContaBancaria")
    lancamentos_gerados = relationship(
        "LancamentoManual", back_populates="lancamento_recorrente"
    )


# ============================================================================
# MODELS DE CONCILIAÇÃO BANCÁRIA
# ============================================================================
