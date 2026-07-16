# -*- coding: utf-8 -*-
"""Modelos de lembretes e variacoes de produtos."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base_models import BaseTenantModel


# ====================
# LEMBRETES E NOTIFICA��ES
# ====================


class Lembrete(BaseTenantModel):
    """Sistema de lembretes para produtos recorrentes (medicamentos, ra��es, etc)"""

    __tablename__ = "lembretes"

    id = Column(Integer, primary_key=True)

    # Relacionamentos
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    # Reposicoes aprendidas (ex.: racao) podem nao estar vinculadas a um pet.
    # Protocolos continuam usando pet_id quando a venda informa o animal.
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=True, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    venda_id = Column(
        Integer, ForeignKey("vendas.id"), nullable=True, index=True
    )  # Venda que originou o lembrete

    # Datas
    data_compra = Column(DateTime, nullable=True)  # Quando foi comprado
    data_proxima_dose = Column(
        DateTime, nullable=False, index=True
    )  # Quando deve tomar/comprar novamente
    data_notificacao_7_dias = Column(
        DateTime, nullable=True
    )  # Quando enviar notifica��o (7 dias antes)
    data_notificacao_enviada = Column(
        DateTime, nullable=True
    )  # Quando foi efetivamente enviado
    data_completado = Column(
        DateTime, nullable=True
    )  # Quando o cliente confirmou a compra/dose

    # Status
    status = Column(
        String(20), default="pendente"
    )  # pendente, notificado, completado, cancelado
    metodo_notificacao = Column(String(50), default="app")
    notificacao_enviada = Column(Boolean, default=False)

    # Como o intervalo foi definido. Estes campos deixam a previsao auditavel
    # para a loja e evitam tratar uma estimativa como se fosse um protocolo.
    origem_intervalo = Column(String(30), nullable=True)  # configurado, aprendido
    intervalo_estimado_dias = Column(Integer, nullable=True)
    confianca_recorrencia = Column(Float, nullable=True)
    amostras_recorrencia = Column(Integer, nullable=False, default=0)

    # Informa��es adicionais
    observacoes = Column(Text, nullable=True)
    quantidade_recomendada = Column(Float, nullable=True)  # Quantidade a comprar/usar
    preco_estimado = Column(Float, nullable=True)  # Pre�o estimado na pr�xima compra

    # Controle de doses
    dose_atual = Column(Integer, default=1)  # Qual dose o cliente est� (1, 2, 3...)
    dose_total = Column(Integer, nullable=True)  # Total de doses necess�rias (ex: 3)
    historico_doses = Column(
        Text, nullable=True
    )  # JSON com hist�rico [{dose: 1, data: '2026-01-13', comprou: true}]

    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    cliente = relationship("Cliente")
    pet = relationship("Pet")
    produto = relationship("Produto")


# ============================================================================
# SISTEMA DE ATRIBUTOS E VARIA��ES DE PRODUTOS
# ============================================================================


class ProdutoAtributo(BaseTenantModel):
    """
    Atributos de produtos PAI que definem suas varia��es

    Exemplos:
    - Produto PAI: "Ra��o Golden Adulto"
      - Atributo 1: "Peso" (op��es: 1kg, 3kg, 15kg)
      - Atributo 2: "Sabor" (op��es: Carne, Frango, Cordeiro)

    Regras:
    - Apenas produtos tipo PAI podem ter atributos
    - Cada atributo pode ter m�ltiplas op��es
    - Combina��es de op��es geram varia��es
    """

    __tablename__ = "produtos_atributos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)

    # Relacionamento com produto PAI
    produto_pai_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)

    # Dados do atributo
    nome = Column(String(100), nullable=False)  # Ex: "Peso", "Sabor", "Cor", "Tamanho"
    ordem = Column(Integer, default=0)  # Ordem de exibi��o
    obrigatorio = Column(Boolean, default=True)  # Se obrigat�rio na cria��o de varia��o

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    produto_pai = relationship(
        "Produto", foreign_keys=[produto_pai_id], backref="atributos"
    )
    opcoes = relationship(
        "ProdutoAtributoOpcao", back_populates="atributo", cascade="all, delete-orphan"
    )
    user = relationship("User")

    # �ndices
    __table_args__ = (
        Index("idx_atributos_produto_pai", "produto_pai_id"),
        Index("idx_atributos_user", "user_id"),
        {"extend_existing": True},
    )


class ProdutoAtributoOpcao(BaseTenantModel):
    """
    Op��es/valores de um atributo de produto

    Exemplos:
    - Atributo "Peso" pode ter op��es: "1kg", "3kg", "15kg"
    - Atributo "Sabor" pode ter op��es: "Carne", "Frango", "Cordeiro"

    Regras:
    - Cada op��o pertence a um atributo
    - Varia��es referenciam combina��es de op��es
    """

    __tablename__ = "produtos_atributos_opcoes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)

    # Relacionamento com atributo
    atributo_id = Column(Integer, ForeignKey("produtos_atributos.id"), nullable=False)

    # Dados da op��o
    valor = Column(String(100), nullable=False)  # Ex: "15kg", "Carne", "Vermelho"
    ordem = Column(Integer, default=0)  # Ordem de exibi��o
    ajuste_preco = Column(Float, default=0)  # Ajuste de pre�o em rela��o ao produto PAI
    ajuste_preco_tipo = Column(String(20), default="fixo")  # fixo, percentual
    codigo_extra = Column(
        String(50), nullable=True
    )  # C�digo adicional para varia��o (ex: SKU extra)

    # Auditoria
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    atributo = relationship("ProdutoAtributo", back_populates="opcoes")

    # �ndices
    __table_args__ = (
        Index("idx_opcoes_atributo", "atributo_id"),
        {"extend_existing": True},
    )


class ProdutoVariacaoAtributo(BaseTenantModel):
    """
    Tabela de associa��o entre varia��es e op��es de atributos

    Mapeia quais op��es de atributos comp�em uma varia��o espec�fica

    Exemplo:
    - Varia��o "Ra��o Golden Adulto 15kg Carne"
      - Atributo "Peso" ? Op��o "15kg"
      - Atributo "Sabor" ? Op��o "Carne"

    Regras:
    - Apenas produtos tipo VARIACAO podem ter entradas aqui
    - Cada varia��o deve ter uma op��o de cada atributo obrigat�rio do PAI
    """

    __tablename__ = "produtos_variacoes_atributos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)

    # Relacionamentos
    variacao_id = Column(
        Integer, ForeignKey("produtos.id"), nullable=False
    )  # FK para produto VARIACAO
    atributo_id = Column(Integer, ForeignKey("produtos_atributos.id"), nullable=False)
    opcao_id = Column(
        Integer, ForeignKey("produtos_atributos_opcoes.id"), nullable=False
    )

    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    variacao = relationship(
        "Produto", foreign_keys=[variacao_id], backref="atributos_variacao"
    )
    atributo = relationship("ProdutoAtributo")
    opcao = relationship("ProdutoAtributoOpcao")

    # �ndices e constraints
    __table_args__ = (
        Index("idx_var_atributos_variacao", "variacao_id"),
        Index("idx_var_atributos_atributo", "atributo_id"),
        Index("idx_var_atributos_opcao", "opcao_id"),
        # Constraint: Uma varia��o n�o pode ter a mesma op��o de atributo duplicada
        Index("idx_var_atributos_unique", "variacao_id", "atributo_id", unique=True),
        {"extend_existing": True},
    )
