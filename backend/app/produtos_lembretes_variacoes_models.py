# -*- coding: utf-8 -*-
"""Modelos de lembretes e variacoes de produtos."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base_models import BaseTenantModel

# ====================
# LEMBRETES E NOTIFICAÇÕES
# ====================


class ProdutoProtocoloRecorrencia(BaseTenantModel):
    """Regra de recompra ou protocolo de doses vinculada a um produto."""

    __tablename__ = "produto_protocolos_recorrencia"

    produto_id = Column(
        Integer,
        ForeignKey("produtos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome = Column(String(160), nullable=False)
    tipo = Column(String(30), nullable=False)  # recompra_continua, protocolo_doses
    especie_compativel = Column(String(20), nullable=False, default="both")
    fase_vida = Column(String(20), nullable=False, default="all")
    intervalo_recompra_dias = Column(Integer, nullable=True)
    ajustar_ao_historico = Column(Boolean, nullable=False, default=True)
    reiniciar_apos_dias = Column(Integer, nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)

    produto = relationship("Produto", back_populates="protocolos_recorrencia")
    doses = relationship(
        "ProdutoProtocoloDose",
        back_populates="protocolo",
        cascade="all, delete-orphan",
        order_by="ProdutoProtocoloDose.numero_dose",
    )

    __table_args__ = (
        Index(
            "ix_produto_protocolos_recorrencia_tenant_produto_ativo",
            "tenant_id",
            "produto_id",
            "ativo",
        ),
    )


class ProdutoProtocoloDose(BaseTenantModel):
    """Dose de um protocolo, posicionada em dias desde a primeira dose."""

    __tablename__ = "produto_protocolo_doses"

    protocolo_id = Column(
        Integer,
        ForeignKey("produto_protocolos_recorrencia.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    numero_dose = Column(Integer, nullable=False)
    dias_desde_inicio = Column(Integer, nullable=False)

    protocolo = relationship("ProdutoProtocoloRecorrencia", back_populates="doses")

    __table_args__ = (
        UniqueConstraint(
            "protocolo_id",
            "numero_dose",
            name="uq_produto_protocolo_dose_numero",
        ),
    )


class Lembrete(BaseTenantModel):
    """Sistema de lembretes para produtos recorrentes (medicamentos, rações, etc)"""

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
    protocolo_recorrencia_id = Column(
        Integer,
        ForeignKey("produto_protocolos_recorrencia.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Datas
    data_compra = Column(DateTime, nullable=True)  # Quando foi comprado
    data_proxima_dose = Column(
        DateTime, nullable=False, index=True
    )  # Quando deve tomar/comprar novamente
    data_notificacao_7_dias = Column(
        DateTime, nullable=True
    )  # Quando enviar notificação (7 dias antes)
    data_notificacao_enviada = Column(
        DateTime, nullable=True
    )  # Quando foi efetivamente enviado
    data_completado = Column(
        DateTime, nullable=True
    )  # Quando o cliente confirmou a compra/dose
    data_inicio_protocolo = Column(DateTime, nullable=True)

    # Status
    status = Column(
        String(20), default="pendente"
    )  # pendente, notificado, completado, cancelado
    metodo_notificacao = Column(String(50), default="app")
    notificacao_enviada = Column(Boolean, default=False)
    tipo_lembrete = Column(
        String(30), nullable=False, default="recompra"
    )  # recompra, proxima_dose, reinicio_protocolo

    # Como o intervalo foi definido. Estes campos deixam a previsao auditavel
    # para a loja e evitam tratar uma estimativa como se fosse um protocolo.
    origem_intervalo = Column(String(30), nullable=True)  # configurado, aprendido
    intervalo_estimado_dias = Column(Integer, nullable=True)
    confianca_recorrencia = Column(Float, nullable=True)
    amostras_recorrencia = Column(Integer, nullable=False, default=0)

    # Informações adicionais
    observacoes = Column(Text, nullable=True)
    quantidade_recomendada = Column(Float, nullable=True)  # Quantidade a comprar/usar
    preco_estimado = Column(Float, nullable=True)  # Preço estimado na próxima compra

    # Controle de doses
    dose_atual = Column(Integer, default=1)  # Qual dose o cliente está (1, 2, 3...)
    dose_total = Column(Integer, nullable=True)  # Total de doses necessárias (ex: 3)
    historico_doses = Column(
        Text, nullable=True
    )  # JSON com histórico [{dose: 1, data: '2026-01-13', comprou: true}]

    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    cliente = relationship("Cliente")
    pet = relationship("Pet")
    produto = relationship("Produto")
    protocolo_recorrencia = relationship("ProdutoProtocoloRecorrencia")
    contatos = relationship(
        "LembreteContato", back_populates="lembrete", cascade="all, delete-orphan"
    )


class LembreteContato(BaseTenantModel):
    """Contato feito para uma oportunidade de recompra."""

    __tablename__ = "lembretes_contatos"

    lembrete_id = Column(
        Integer,
        ForeignKey("lembretes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cliente_id = Column(
        Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    produto_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notification_queue_id = Column(
        BigInteger,
        ForeignKey("notification_queue.id", ondelete="SET NULL"),
        nullable=True,
    )
    canal = Column(String(20), nullable=False)
    acao = Column(String(40), nullable=False)
    status = Column(String(30), nullable=False, default="registrado")
    mensagem = Column(Text, nullable=False)
    resultado = Column(String(120), nullable=True)
    idempotency_key = Column(String(300), nullable=True)

    lembrete = relationship("Lembrete", back_populates="contatos")
    cliente = relationship("Cliente")
    produto = relationship("Produto")
    operador = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_lembretes_contatos_tenant_idempotency",
        ),
        Index(
            "ix_lembretes_contatos_tenant_lembrete_created",
            "tenant_id",
            "lembrete_id",
            "created_at",
        ),
        Index(
            "ix_lembretes_contatos_tenant_canal_created",
            "tenant_id",
            "canal",
            "created_at",
        ),
    )


# ============================================================================
# SISTEMA DE ATRIBUTOS E VARIAÇÕES DE PRODUTOS
# ============================================================================


class ProdutoAtributo(BaseTenantModel):
    """
    Atributos de produtos PAI que definem suas variações

    Exemplos:
    - Produto PAI: "Ração Golden Adulto"
      - Atributo 1: "Peso" (opções: 1kg, 3kg, 15kg)
      - Atributo 2: "Sabor" (opções: Carne, Frango, Cordeiro)

    Regras:
    - Apenas produtos tipo PAI podem ter atributos
    - Cada atributo pode ter múltiplas opções
    - Combinações de opções geram variações
    """

    __tablename__ = "produtos_atributos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)

    # Relacionamento com produto PAI
    produto_pai_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)

    # Dados do atributo
    nome = Column(String(100), nullable=False)  # Ex: "Peso", "Sabor", "Cor", "Tamanho"
    ordem = Column(Integer, default=0)  # Ordem de exibição
    obrigatorio = Column(Boolean, default=True)  # Se obrigatório na criação de variação

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

    # Índices
    __table_args__ = (
        Index("idx_atributos_produto_pai", "produto_pai_id"),
        Index("idx_atributos_user", "user_id"),
        {"extend_existing": True},
    )


class ProdutoAtributoOpcao(BaseTenantModel):
    """
    Opções/valores de um atributo de produto

    Exemplos:
    - Atributo "Peso" pode ter opções: "1kg", "3kg", "15kg"
    - Atributo "Sabor" pode ter opções: "Carne", "Frango", "Cordeiro"

    Regras:
    - Cada opção pertence a um atributo
    - Variações referenciam combinações de opções
    """

    __tablename__ = "produtos_atributos_opcoes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)

    # Relacionamento com atributo
    atributo_id = Column(Integer, ForeignKey("produtos_atributos.id"), nullable=False)

    # Dados da opção
    valor = Column(String(100), nullable=False)  # Ex: "15kg", "Carne", "Vermelho"
    ordem = Column(Integer, default=0)  # Ordem de exibição
    ajuste_preco = Column(Float, default=0)  # Ajuste de preço em relação ao produto PAI
    ajuste_preco_tipo = Column(String(20), default="fixo")  # fixo, percentual
    codigo_extra = Column(
        String(50), nullable=True
    )  # Código adicional para variação (ex: SKU extra)

    # Auditoria
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    atributo = relationship("ProdutoAtributo", back_populates="opcoes")

    # Índices
    __table_args__ = (
        Index("idx_opcoes_atributo", "atributo_id"),
        {"extend_existing": True},
    )


class ProdutoVariacaoAtributo(BaseTenantModel):
    """
    Tabela de associação entre variações e opções de atributos

    Mapeia quais opções de atributos compõem uma variação específica

    Exemplo:
    - Variação "Ração Golden Adulto 15kg Carne"
      - Atributo "Peso" ? Opção "15kg"
      - Atributo "Sabor" ? Opção "Carne"

    Regras:
    - Apenas produtos tipo VARIACAO podem ter entradas aqui
    - Cada variação deve ter uma opção de cada atributo obrigatório do PAI
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

    # Índices e constraints
    __table_args__ = (
        Index("idx_var_atributos_variacao", "variacao_id"),
        Index("idx_var_atributos_atributo", "atributo_id"),
        Index("idx_var_atributos_opcao", "opcao_id"),
        # Constraint: Uma variação não pode ter a mesma opção de atributo duplicada
        Index("idx_var_atributos_unique", "variacao_id", "atributo_id", unique=True),
        {"extend_existing": True},
    )
