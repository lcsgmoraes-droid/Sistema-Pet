"""Payable and receivable account models for finance."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class ContaPagar(BaseTenantModel):
    """Contas a pagar (despesas)"""

    __tablename__ = "contas_pagar"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(255), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey("clientes.id"))
    categoria_id = Column(
        Integer, ForeignKey("categorias_financeiras.id")
    )  # UX/Agrupamento
    tipo_despesa_id = Column(
        Integer, ForeignKey("tipo_despesas.id"), nullable=True, index=True
    )

    # ============================
    # VINCULO COM DRE (OBRIGATORIO)
    # ============================
    dre_subcategoria_id = Column(
        Integer,
        nullable=True,  # Opcional para compras sem classificação DRE ainda
        index=True,
        comment="Subcategoria DRE - fonte da verdade contábil",
    )
    canal = Column(
        String(50),
        nullable=True,  # Opcional para compras (não é venda)
        index=True,
        comment="Canal de venda: loja_fisica, mercado_livre, shopee, amazon",
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
    status = Column(
        String(20), default="pendente", index=True
    )  # 'pendente', 'pago', 'vencido', 'cancelado', 'parcial'

    # Parcelamento
    eh_parcelado = Column(Boolean, default=False)
    numero_parcela = Column(Integer)
    total_parcelas = Column(Integer)
    conta_principal_id = Column(Integer, ForeignKey("contas_pagar.id"))

    # Recorrência
    eh_recorrente = Column(Boolean, default=False)
    tipo_recorrencia = Column(
        String(20)
    )  # 'semanal' (7 dias), 'quinzenal' (15 dias), 'mensal', 'personalizado'
    intervalo_dias = Column(
        Integer
    )  # Para recorrências personalizadas (ex: 10, 20, 45 dias)
    data_inicio_recorrencia = Column(Date)
    data_fim_recorrencia = Column(Date)  # Opcional: quando a recorrência deve parar
    numero_repeticoes = Column(Integer)  # Opcional: quantas vezes deve repetir
    proxima_recorrencia = Column(Date)
    conta_recorrencia_origem_id = Column(
        Integer, ForeignKey("contas_pagar.id")
    )  # ID da conta que originou esta

    # Referências
    nota_entrada_id = Column(Integer, ForeignKey("notas_entrada.id"), index=True)
    # lancamento_manual_id = Column(Integer, ForeignKey('lancamentos_manuais.id'), index=True)  # TEMPORARIAMENTE DESABILITADO
    nfe_numero = Column(String(50))
    documento = Column(String(100))
    observacoes = Column(Text)

    # Classificacao DRE automatica/aprendizado
    beneficiario = Column(String(255), nullable=True)
    tipo_documento = Column(String(50), nullable=True)
    afeta_dre = Column(Boolean, default=True, nullable=False)

    # Rateio Online vs Loja Física (para filtros e relatórios)
    percentual_online = Column(
        Float, default=0
    )  # % desta conta que é referente a vendas online
    percentual_loja = Column(
        Float, default=100
    )  # % desta conta que é referente a loja física

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
    categoria = relationship("CategoriaFinanceira", back_populates="contas_pagar")
    tipo_despesa = relationship("TipoDespesa", back_populates="contas")
    pagamentos = relationship(
        "Pagamento", back_populates="conta", cascade="all, delete-orphan"
    )
    parcelas = relationship(
        "ContaPagar",
        backref="conta_principal",
        remote_side=[id],
        foreign_keys=[conta_principal_id],
    )


class ContaReceber(BaseTenantModel):
    """Contas a receber (receitas)"""

    __tablename__ = "contas_receber"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(255), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    categoria_id = Column(
        Integer, ForeignKey("categorias_financeiras.id")
    )  # UX/Agrupamento
    forma_pagamento_id = Column(Integer, ForeignKey("formas_pagamento.id"))

    # ============================
    # VINCULO COM DRE (OBRIGATORIO)
    # ============================
    dre_subcategoria_id = Column(
        Integer,
        nullable=False,
        index=True,
        comment="Subcategoria DRE - fonte da verdade contábil",
    )
    canal = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Canal de venda: loja_fisica, mercado_livre, shopee, amazon",
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
    status = Column(
        String(20), default="pendente", index=True
    )  # 'pendente', 'recebido', 'vencido', 'cancelado', 'parcial'

    # Parcelamento
    eh_parcelado = Column(Boolean, default=False)
    numero_parcela = Column(Integer)
    total_parcelas = Column(Integer)
    conta_principal_id = Column(Integer, ForeignKey("contas_receber.id"))

    # Recorrência
    eh_recorrente = Column(Boolean, default=False)
    tipo_recorrencia = Column(
        String(20)
    )  # 'semanal' (7 dias), 'quinzenal' (15 dias), 'mensal', 'personalizado'
    intervalo_dias = Column(Integer)  # Para recorrências personalizadas
    data_inicio_recorrencia = Column(Date)
    data_fim_recorrencia = Column(Date)
    numero_repeticoes = Column(Integer)
    proxima_recorrencia = Column(Date)
    conta_recorrencia_origem_id = Column(Integer, ForeignKey("contas_receber.id"))

    # Referências
    venda_id = Column(Integer, ForeignKey("vendas.id", ondelete="CASCADE"), index=True)
    # lancamento_manual_id = Column(Integer, ForeignKey('lancamentos_manuais.id'), index=True)  # TEMPORARIAMENTE DESABILITADO
    nfe_numero = Column(String(50))
    documento = Column(String(100))
    observacoes = Column(Text)

    # Classificacao DRE automatica/aprendizado
    beneficiario = Column(String(255), nullable=True)
    tipo_documento = Column(String(50), nullable=True)

    # ============================
    # CONCILIAÇÃO DE CARTÃO (FASE 3)
    # ============================
    nsu = Column(
        String(100), nullable=True, index=True, comment="NSU da transação de cartão"
    )
    adquirente = Column(
        String(50), nullable=True, comment="Adquirente (Stone, Cielo, etc)"
    )
    conciliado = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Se a transação foi conciliada",
    )
    data_conciliacao = Column(
        Date, nullable=True, comment="Data em que a conciliação foi realizada"
    )

    # ============================
    # CONCILIAÇÃO COMPLETA (FASE 1+2) - Ajustes #1-#7
    # ============================
    # Status detalhado (Ajuste #1)
    status_conciliacao = Column(
        String(50),
        default="prevista",
        index=True,
        comment="prevista|confirmada_operadora|aguardando_lote|em_lote|liquidada",
    )

    # Taxas estimadas (calculadas no PDV - Ajuste #9)
    taxa_mdr_estimada = Column(
        Numeric(5, 2), nullable=True, comment="MDR calculado no PDV"
    )
    taxa_antecipacao_estimada = Column(
        Numeric(5, 2), nullable=True, comment="Taxa de antecipação calculada"
    )

    # Taxas reais (importadas do arquivo da operadora)
    taxa_mdr_real = Column(
        Numeric(5, 2), nullable=True, comment="MDR real do arquivo operadora"
    )
    taxa_antecipacao_real = Column(
        Numeric(5, 2), nullable=True, comment="Taxa real do arquivo"
    )

    # Valores líquidos
    valor_liquido_estimado = Column(
        Numeric(15, 2), nullable=True, comment="Valor bruto - taxas estimadas"
    )
    valor_liquido_real = Column(
        Numeric(15, 2), nullable=True, comment="Valor líquido do arquivo operadora"
    )

    # Datas de vencimento
    data_vencimento_estimada = Column(
        Date, nullable=True, comment="Vencimento calculado (D+X)"
    )
    data_vencimento_real = Column(
        Date, nullable=True, comment="Vencimento informado pela operadora"
    )

    # ============================
    # AMARRAÇÃO VENDA ↔ RECEBIMENTO (NOVA ARQUITETURA 3 ABAS)
    # ============================
    tipo_recebimento = Column(
        String(30),
        nullable=True,
        comment="antecipacao (todas parcelas) | parcela_individual (1/3, 2/3, etc)",
    )
    # FK desabilitado - tabela conciliacao_recebimentos pode não estar registrada
    conciliacao_recebimento_id = Column(
        Integer,
        # was: ForeignKey('conciliacao_recebimentos.id'),
        nullable=True,
        index=True,
        comment="FK para recebimento Stone (idempotência)",
    )

    # Divergências (para alertas - Ajuste #10)
    diferenca_taxa = Column(
        Numeric(5, 2), nullable=True, comment="MDR real - MDR estimado"
    )
    diferenca_valor = Column(
        Numeric(15, 2), nullable=True, comment="Valor líquido real - estimado"
    )

    # Vínculo com lotes (Ajuste #3) - FK desabilitado
    conciliacao_lote_id = Column(
        Integer, nullable=True
    )  # was: ForeignKey('conciliacao_lotes.id', ondelete='SET NULL')

    # Vínculo com validação (FK desabilitado - tabela conciliacao_validacoes não existe)
    validacao_id = Column(
        Integer,
        # was: ForeignKey('conciliacao_validacoes.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment="Validação que processou esta parcela (evita reprocessamento)",
    )

    # Versionamento (Ajuste #7)
    versao_conciliacao = Column(
        Integer, default=1, comment="Incrementa a cada reprocessamento"
    )

    # Data de liquidação efetiva
    data_liquidacao = Column(
        Date,
        nullable=True,
        index=True,
        comment="Data em que o dinheiro entrou na conta",
    )

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    categoria = relationship("CategoriaFinanceira", back_populates="contas_receber")
    forma_pagamento = relationship("FormaPagamento", back_populates="contas_receber")
    recebimentos = relationship(
        "Recebimento", back_populates="conta", cascade="all, delete-orphan"
    )
    parcelas = relationship(
        "ContaReceber",
        backref="conta_principal",
        remote_side=[id],
        foreign_keys=[conta_principal_id],
    )
    # lote = relationship("ConciliacaoLote", foreign_keys=[conciliacao_lote_id], back_populates="parcelas")  # TODO: Criar modelo ConciliacaoLote


class Pagamento(BaseTenantModel):
    """Registro de pagamentos (baixas de contas a pagar)"""

    __tablename__ = "pagamentos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    conta_pagar_id = Column(
        Integer, ForeignKey("contas_pagar.id"), nullable=False, index=True
    )
    forma_pagamento_id = Column(Integer, ForeignKey("formas_pagamento.id"))

    valor_pago = Column(Numeric(10, 2), nullable=False)
    data_pagamento = Column(Date, nullable=False, index=True)

    observacoes = Column(Text)
    comprovante = Column(String(255))

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conta = relationship("ContaPagar", back_populates="pagamentos")
    forma_pagamento = relationship("FormaPagamento", back_populates="pagamentos")


class Recebimento(BaseTenantModel):
    """Registro de recebimentos (baixas de contas a receber)"""

    __tablename__ = "recebimentos"
    __table_args__ = {"extend_existing": True}

    # Override BaseTenantModel's updated_at since this table doesn't have it
    updated_at = None

    id = Column(Integer, primary_key=True, index=True)
    conta_receber_id = Column(
        Integer,
        ForeignKey("contas_receber.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forma_pagamento_id = Column(Integer, ForeignKey("formas_pagamento.id"))

    valor_recebido = Column(Numeric(10, 2), nullable=False)
    data_recebimento = Column(Date, nullable=False, index=True)

    observacoes = Column(Text)
    comprovante = Column(String(255))

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conta = relationship("ContaReceber", back_populates="recebimentos")
    forma_pagamento = relationship("FormaPagamento", back_populates="recebimentos")


# ============================================================================
# NOVAS CLASSES - FASE 1: Base Financeira
# ============================================================================
