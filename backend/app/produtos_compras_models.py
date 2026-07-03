# -*- coding: utf-8 -*-
"""Modelos de pedidos de compra, notas de entrada e historico de precos."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base_models import BaseTenantModel


# ============================================================================
# PEDIDOS DE COMPRA
# ============================================================================


class PedidoCompra(BaseTenantModel):
    """Pedidos de compra de produtos (com suporte futuro para IA)"""

    __tablename__ = "pedidos_compra"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    numero_pedido = Column(String(50), unique=True, nullable=False, index=True)
    fornecedor_id = Column(Integer, nullable=False, index=True)  # FK para clientes

    # Status: rascunho, enviado, confirmado, recebido_parcial, recebido_total, cancelado
    status = Column(String(20), nullable=False, default="rascunho", index=True)

    # Valores
    valor_total = Column(Float, nullable=False, default=0)
    valor_frete = Column(Float, default=0)
    valor_desconto = Column(Float, default=0)
    valor_final = Column(Float, nullable=False, default=0)

    # Datas
    data_pedido = Column(DateTime, nullable=False, default=datetime.utcnow)
    data_prevista_entrega = Column(DateTime)
    data_recebimento = Column(DateTime)
    data_envio = Column(DateTime)
    data_confirmacao = Column(DateTime)

    # Observa��es e IA
    observacoes = Column(Text)
    foi_alterado_apos_envio = Column(
        Boolean, default=False
    )  # Flag para alertar mudan�as
    sugestao_ia = Column(Boolean, default=False)  # Se foi sugerido por IA
    confianca_ia = Column(Float)  # 0-1: Confian�a da sugest�o
    dados_ia = Column(Text)  # JSON com an�lise da IA

    # Confronto com NF-e
    nota_entrada_id = Column(
        Integer, ForeignKey("notas_entrada.id"), nullable=True, index=True
    )
    data_confronto = Column(DateTime, nullable=True)
    status_confronto = Column(
        String(30), nullable=True
    )  # sem_divergencia, divergencia_quantidade, divergencia_preco, divergencia_mista
    resumo_confronto = Column(Text, nullable=True)  # JSON com detalhes do confronto
    confronto_finalizado = Column(
        Boolean, default=False
    )  # True = confronto encerrado, link permanente

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    itens = relationship(
        "PedidoCompraItem", back_populates="pedido", cascade="all, delete-orphan"
    )
    notas_entrada_vinculos = relationship(
        "PedidoCompraNotaEntrada", back_populates="pedido", cascade="all, delete-orphan"
    )
    user = relationship("User", foreign_keys=[user_id])


class PedidoCompraNotaEntrada(BaseTenantModel):
    """Vinculos entre um pedido de compra e uma ou mais notas fiscais de entrada."""

    __tablename__ = "pedidos_compra_notas_entrada"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "pedido_compra_id",
            "nota_entrada_id",
            name="uq_pedido_compra_nota_entrada",
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    pedido_compra_id = Column(
        Integer, ForeignKey("pedidos_compra.id"), nullable=False, index=True
    )
    nota_entrada_id = Column(
        Integer, ForeignKey("notas_entrada.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pedido = relationship("PedidoCompra", back_populates="notas_entrada_vinculos")
    nota = relationship("NotaEntrada", back_populates="pedidos_compra_vinculos")
    user = relationship("User", foreign_keys=[user_id])


class PedidoCompraItem(BaseTenantModel):
    """Itens de pedidos de compra"""

    __tablename__ = "pedidos_compra_itens"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    pedido_compra_id = Column(
        Integer, ForeignKey("pedidos_compra.id"), nullable=False, index=True
    )
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)

    # Quantidades
    quantidade_pedida = Column(Float, nullable=False)
    quantidade_recebida = Column(Float, default=0)
    unidade_compra = Column(String(10), nullable=False, default="UN")
    quantidade_por_embalagem = Column(Float, nullable=True)
    quantidade_total_unidades = Column(Float, nullable=False, default=0)

    # Valores
    preco_unitario = Column(Float, nullable=False)
    desconto_item = Column(Float, default=0)
    valor_total = Column(Float, nullable=False)

    # Status do item
    status = Column(
        String(20), default="pendente"
    )  # pendente, recebido_parcial, recebido_total, cancelado

    # IA
    sugestao_ia = Column(Boolean, default=False)
    motivo_ia = Column(Text)  # Por que a IA sugeriu este item

    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pedido = relationship("PedidoCompra", back_populates="itens")
    produto = relationship("Produto")


# ============================================================================
# NOTAS DE ENTRADA (NF-e de Fornecedores)
# ============================================================================


class NotaEntrada(BaseTenantModel):
    """Notas fiscais de entrada (NF-e de fornecedores)"""

    __tablename__ = "notas_entrada"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    numero_nota = Column(String(20), nullable=False, index=True)
    serie = Column(String(5), nullable=False)
    chave_acesso = Column(String(44), unique=True, nullable=False, index=True)

    # Fornecedor
    fornecedor_cnpj = Column(String(18), nullable=False)
    fornecedor_nome = Column(String(255), nullable=False)
    fornecedor_id = Column(Integer, index=True)  # Link com clientes (fornecedores)

    # Datas
    data_emissao = Column(DateTime, nullable=False)
    data_entrada = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Valores
    valor_produtos = Column(Float, nullable=False)
    valor_frete = Column(Float, default=0)
    valor_desconto = Column(Float, default=0)
    valor_total = Column(Float, nullable=False)

    # XML
    xml_content = Column(Text, nullable=False)

    # Status: pendente, processada, erro
    status = Column(String(20), default="pendente", index=True)
    erro_mensagem = Column(Text)

    # Conferência física da NF
    conferencia_status = Column(String(30), default="nao_iniciada", index=True)
    conferencia_observacoes = Column(Text)
    conferencia_realizada_em = Column(DateTime)
    conferencia_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )

    # Processamento
    processada_em = Column(DateTime)
    produtos_vinculados = Column(Integer, default=0)
    produtos_nao_vinculados = Column(Integer, default=0)
    entrada_estoque_realizada = Column(Boolean, default=False)
    processamento_contexto = Column(String(30), nullable=True)
    processamento_acoes = Column(Text, nullable=True)

    # Rateio Online vs Loja Física (apenas informativo/analítico - estoque é UNIFICADO)
    tipo_rateio = Column(String(20), default="loja")  # 'online', 'loja', 'parcial'
    percentual_online = Column(Float, default=0)  # % do valor total que é online
    percentual_loja = Column(Float, default=100)  # % do valor total que é loja
    valor_online = Column(Float, default=0)  # R$ referente a online
    valor_loja = Column(Float, default=0)  # R$ referente a loja física

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    itens = relationship(
        "NotaEntradaItem", back_populates="nota", cascade="all, delete-orphan"
    )
    pedidos_compra_vinculos = relationship(
        "PedidoCompraNotaEntrada", back_populates="nota", cascade="all, delete-orphan"
    )
    user = relationship("User", foreign_keys=[user_id])
    conferencia_user = relationship("User", foreign_keys=[conferencia_user_id])


class NotaEntradaItem(BaseTenantModel):
    """Itens da nota fiscal de entrada"""

    __tablename__ = "notas_entrada_itens"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    nota_entrada_id = Column(
        Integer, ForeignKey("notas_entrada.id"), nullable=False, index=True
    )

    # Dados do XML
    numero_item = Column(Integer, nullable=False)
    codigo_produto = Column(String(100))
    descricao = Column(String(500), nullable=False)
    ncm = Column(String(8))
    cest = Column(String(7))  # C�digo CEST do produto
    cfop = Column(String(4))
    origem = Column(String(1))  # Origem da mercadoria (0-8)
    aliquota_icms = Column(Float, default=0)  # Al�quota ICMS (%)
    aliquota_pis = Column(Float, default=0)  # Al�quota PIS (%)
    aliquota_cofins = Column(Float, default=0)  # Al�quota COFINS (%)
    unidade = Column(String(10))
    quantidade = Column(Float, nullable=False)
    valor_unitario = Column(Float, nullable=False)
    valor_total = Column(Float, nullable=False)
    ean = Column(String(14))  # Codigo de barras EAN comercial
    ean_tributario = Column(String(14))  # Codigo de barras EAN tributario/fiscal
    lote = Column(String(50))  # Lote do produto
    data_validade = Column(Date)  # Data de validade

    # Vincula��o
    produto_id = Column(Integer, ForeignKey("produtos.id"), index=True)
    vinculado = Column(Boolean, default=False)
    confianca_vinculo = Column(Float)  # 0-1

    # Status: pendente, vinculado, nao_vinculado, processado
    status = Column(String(20), default="pendente")

    # Conferência física
    quantidade_conferida = Column(Float, nullable=True)
    quantidade_avariada = Column(Float, default=0)
    observacao_conferencia = Column(Text)
    acao_sugerida = Column(String(40), default="sem_acao")

    # Rateio (apenas para análise/relatórios - estoque é UNIFICADO)
    quantidade_online = Column(
        Float, default=0
    )  # Quantidade deste item que é do online
    valor_online = Column(
        Float, default=0
    )  # Valor calculado: quantidade_online × valor_unitario

    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    nota = relationship("NotaEntrada", back_populates="itens")
    produto = relationship("Produto", foreign_keys=[produto_id])


class ProdutoHistoricoPreco(BaseTenantModel):
    """Hist�rico de altera��es de pre�os de produtos"""

    __tablename__ = "produtos_historico_precos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)

    # Pre�os anteriores e novos
    preco_custo_anterior = Column(Float)
    preco_custo_novo = Column(Float)
    preco_venda_anterior = Column(Float)
    preco_venda_novo = Column(Float)
    margem_anterior = Column(Float)
    margem_nova = Column(Float)

    # Varia��es percentuais
    variacao_custo_percentual = Column(Float)  # % de varia��o do custo
    variacao_venda_percentual = Column(Float)  # % de varia��o do pre�o venda

    # Contexto da altera��o
    motivo = Column(String(100))  # 'nfe_entrada', 'manual', 'promocao', 'reajuste'
    nota_entrada_id = Column(
        Integer, ForeignKey("notas_entrada.id"), nullable=True, index=True
    )
    referencia = Column(String(100))  # n�mero da nota, descri��o, etc
    observacoes = Column(Text)

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    produto = relationship("Produto", foreign_keys=[produto_id])
    nota_entrada = relationship("NotaEntrada", foreign_keys=[nota_entrada_id])
    user = relationship("User", foreign_keys=[user_id])
