"""Catalog and payment method models for finance."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class CategoriaFinanceira(BaseTenantModel):
    """Categorias para organizar receitas e despesas"""

    __tablename__ = "categorias_financeiras"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(String(20), nullable=False)  # 'receita' ou 'despesa'
    cor = Column(String(7))
    icone = Column(String(50))
    descricao = Column(Text)
    categoria_pai_id = Column(Integer, ForeignKey("categorias_financeiras.id"))
    ativo = Column(Boolean, default=True)

    # ============================
    # VINCULO COM DRE (NOVO)
    # ============================
    dre_subcategoria_id = Column(
        Integer, ForeignKey("dre_subcategorias.id"), nullable=True
    )
    tipo_custo = Column(String(10), nullable=True)  # 'fixo', 'variavel', 'ambos'

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    categoria_pai = relationship(
        "CategoriaFinanceira", remote_side=[id], backref="subcategorias"
    )
    contas_pagar = relationship("ContaPagar", back_populates="categoria")
    contas_receber = relationship("ContaReceber", back_populates="categoria")


class FormaPagamento(BaseTenantModel):
    """Formas de pagamento disponíveis"""

    __tablename__ = "formas_pagamento"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(
        String(20), nullable=False
    )  # 'dinheiro', 'cartao_credito', 'cartao_debito', 'pix', 'boleto', 'transferencia'

    # Taxas e prazos (FASE 1 - novos)
    taxa_percentual = Column(Numeric(5, 2), default=0)
    taxa_fixa = Column(Numeric(10, 2), default=0)
    prazo_dias = Column(Integer, default=0)  # Prazo para recebimento
    prazo_recebimento = Column(Integer, default=0)  # dias (manter compatibilidade)

    # Configurações (FASE 1 - novos)
    operadora = Column(String(50))  # Stone, Cielo, Rede, etc
    gera_contas_receber = Column(Boolean, default=False)
    split_parcelas = Column(Boolean, default=False)
    conta_bancaria_destino_id = Column(Integer, ForeignKey("contas_bancarias.id"))
    requer_nsu = Column(Boolean, default=False)
    tipo_cartao = Column(String(20))  # debito, credito, voucher
    bandeira = Column(String(20))  # visa, master, elo, amex

    # Parcelamento
    ativo = Column(Boolean, default=True)
    permite_parcelamento = Column(Boolean, default=False)
    max_parcelas = Column(Integer, default=1)
    parcelas_maximas = Column(Integer, default=1)  # manter compatibilidade
    taxas_por_parcela = Column(
        Text
    )  # JSON com taxas específicas por número de parcelas

    # Operadora de Cartão (FK desabilitado - tabela operadoras_cartao não existe)
    operadora_id = Column(
        Integer, nullable=True, index=True
    )  # was: ForeignKey('operadoras_cartao.id')

    # Antecipação de recebíveis
    permite_antecipacao = Column(Boolean, default=False)
    dias_recebimento_antecipado = Column(
        Integer
    )  # Em quantos dias o dinheiro cai com antecipação
    taxa_antecipacao_percentual = Column(
        Numeric(5, 2)
    )  # Taxa adicional para antecipação (opcional)

    # UI
    icone = Column(String(50))
    cor = Column(String(7))

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conta_bancaria_destino = relationship(
        "ContaBancaria", foreign_keys=[conta_bancaria_destino_id]
    )
    # operadora_cartao = relationship("OperadoraCartao", foreign_keys=[operadora_id])  # Disabled - tabela não existe
    contas_receber = relationship("ContaReceber", back_populates="forma_pagamento")
    pagamentos = relationship("Pagamento", back_populates="forma_pagamento")
    recebimentos = relationship("Recebimento", back_populates="forma_pagamento")


class TipoDespesa(BaseTenantModel):
    """
    Tipo de despesa — define se é FIXA ou VARIÁVEL.
    Exemplos: Aluguel (fixo), Salários (fixo), Fornecedor Produto (variável), Impostos (fixo).
    """

    __tablename__ = "tipo_despesas"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    e_custo_fixo = Column(
        Boolean, nullable=False, default=True
    )  # True = Fixo, False = Variável
    dre_subcategoria_id = Column(
        Integer, ForeignKey("dre_subcategorias.id"), nullable=False
    )
    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contas = relationship("ContaPagar", back_populates="tipo_despesa")
