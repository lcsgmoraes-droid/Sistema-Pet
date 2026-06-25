# -*- coding: utf-8 -*-
"""Modelos de estoque, lotes, precos e sincronizacao de produtos."""

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
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base_models import BaseTenantModel
from .services.product_image_storage import build_product_thumbnail_url


class ProdutoImagem(BaseTenantModel):
    """Imagens do produto"""

    __tablename__ = "produto_imagens"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    produto_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False
    )
    url = Column(String(255), nullable=False)
    ordem = Column(Integer, default=0)
    e_principal = Column(Boolean, default=False)
    tamanho = Column(Integer, nullable=True)  # bytes
    largura = Column(Integer, nullable=True)  # pixels
    altura = Column(Integer, nullable=True)  # pixels
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    produto = relationship("Produto", back_populates="imagens")

    @property
    def thumbnail_url(self):
        return build_product_thumbnail_url(self.url)


class ProdutoKitComponente(BaseTenantModel):
    """
    Componentes de um produto KIT

    Define quais produtos fazem parte de um KIT e em que quantidade.
    Exemplo: Kit Banho = Shampoo (1un) + Condicionador (1un) + Toalha (2un)

    ?? RESTRI��ES DE DOM�NIO (OBRIGAT�RIAS):
    ========================================

    1. kit_id - DEVE referenciar Produto com tipo_produto='KIT'
       ? PROIBIDO: tipo_produto IN ('SIMPLES', 'PAI', 'VARIACAO')

    2. produto_componente_id - DEVE referenciar:
       ? Produtos com tipo_produto='SIMPLES'
       ? Produtos com tipo_produto='VARIACAO'
       ? PROIBIDO: tipo_produto='KIT' (KIT n�o pode conter outro KIT)
       ? PROIBIDO: tipo_produto='PAI' (PAI n�o � vend�vel/utiliz�vel)

    3. quantidade - DEVE ser maior que 0 (zero)

    4. Produto componente N�O pode ser o pr�prio KIT (evitar recurs�o)

    Comportamento por tipo_kit:
    - VIRTUAL: Custo do KIT = soma(componente.preco_custo * quantidade)
    - FISICO: Custo do KIT = preco_custo do pr�prio KIT (ignora componentes para custo)

    ?? VALIDA��ES devem ser implementadas na camada de Service (kit_custo_service.py)
    """

    __tablename__ = "produto_kit_componentes"
    __table_args__ = (
        Index("idx_kit_componentes_kit", "kit_id"),
        Index("idx_kit_componentes_produto", "produto_componente_id"),
        # Um produto n�o pode ser componente duplicado no mesmo kit
        Index(
            "idx_kit_componentes_unique", "kit_id", "produto_componente_id", unique=True
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)

    # ?? PROTE��O: kit_id DEVE ser tipo_produto='KIT'
    kit_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False
    )

    # ?? PROTE��O: produto_componente_id DEVE ser tipo_produto IN ('SIMPLES', 'VARIACAO')
    # ? N�O aceitar tipo_produto='KIT' ou 'PAI'
    produto_componente_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)

    # Quantidade do componente no KIT
    quantidade = Column(Float, nullable=False, default=1.0)

    # Componente � opcional? (para kits customiz�veis no futuro)
    opcional = Column(Boolean, default=False)

    # Ordem de exibi��o
    ordem = Column(Integer, default=0)

    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kit = relationship("Produto", foreign_keys=[kit_id], backref="componentes_kit")
    produto_componente = relationship("Produto", foreign_keys=[produto_componente_id])


class ProdutoGranelVinculo(BaseTenantModel):
    """Vinculo entre produto fechado de origem e produto granel abastecido em kg."""

    __tablename__ = "produto_granel_vinculos"
    __table_args__ = (
        Index("idx_produto_granel_vinculo_origem", "tenant_id", "produto_origem_id"),
        Index("idx_produto_granel_vinculo_granel", "tenant_id", "produto_granel_id"),
        UniqueConstraint(
            "tenant_id",
            "produto_origem_id",
            "produto_granel_id",
            name="uq_produto_granel_vinculo_origem_granel",
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)
    produto_origem_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    produto_granel_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    observacao = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    produto_origem = relationship("Produto", foreign_keys=[produto_origem_id])
    produto_granel = relationship("Produto", foreign_keys=[produto_granel_id])
    user = relationship("User")


class GranelConversao(BaseTenantModel):
    """Conversoes rastreadas de pacote fechado para estoque granel em kg."""

    __tablename__ = "granel_conversoes"
    __table_args__ = (
        Index("idx_granel_conversoes_tenant_created", "tenant_id", "created_at"),
        Index("idx_granel_conversoes_granel", "produto_granel_id"),
        Index("idx_granel_conversoes_origem", "produto_origem_id"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)
    produto_granel_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    produto_origem_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade_origem = Column(Float, nullable=False)
    peso_por_unidade_kg = Column(Float, nullable=False)
    quantidade_granel_kg = Column(Float, nullable=False)
    estoque_origem_anterior = Column(Float, nullable=True)
    estoque_origem_novo = Column(Float, nullable=True)
    estoque_granel_anterior = Column(Float, nullable=True)
    estoque_granel_novo = Column(Float, nullable=True)
    documento = Column(String(50), nullable=True)
    observacao = Column(Text, nullable=True)
    status = Column(String(20), default="confirmado", nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    produto_granel = relationship("Produto", foreign_keys=[produto_granel_id])
    produto_origem = relationship("Produto", foreign_keys=[produto_origem_id])
    user = relationship("User")


class ProdutoLote(BaseTenantModel):
    """Lotes de produtos com controle FIFO"""

    __tablename__ = "produto_lotes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    produto_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False
    )

    # ========== SPRINT 2: SUPORTE A VARIA��ES ==========
    # CORRIGIDO: N�o existe tabela product_variations separada
    # Varia��es s�o produtos com tipo_produto='VARIACAO' na tabela produtos
    product_variation_id = Column(
        Integer, nullable=True
    )  # ?? DEPRECATED: usar produto_id

    nome_lote = Column(String(50), nullable=False)
    data_fabricacao = Column(DateTime, nullable=True)
    data_validade = Column(DateTime, nullable=True)
    deposito = Column(String(50), nullable=True)

    # Quantidades
    quantidade_inicial = Column(Float, nullable=False)
    quantidade_disponivel = Column(Float, nullable=False)
    quantidade_reservada = Column(Float, default=0)

    limite_dias = Column(Integer, default=30)
    codigo_agregacao = Column(String(50), nullable=True)
    status = Column(String(20), default="ativo")  # ativo, vencido, bloqueado, esgotado
    ordem_entrada = Column(Integer, nullable=False)  # Timestamp Unix para FIFO
    custo_unitario = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    produto = relationship("Produto", back_populates="lotes")

    # ========== SPRINT 2: SUPORTE A VARIA��ES ==========
    # ? DESABILITADO: ProductVariation removido - causava conflitos
    # variation = relationship("ProductVariation", backref="lotes")

    @property
    def dias_para_vencer(self):
        """Calcula quantos dias faltam para vencer"""
        if not self.data_validade:
            return None
        delta = self.data_validade - datetime.utcnow()
        return delta.days

    @property
    def alerta_vencimento(self):
        """Verifica se está próximo ao vencimento"""
        dias = self.dias_para_vencer
        return dias is not None and dias <= self.limite_dias and dias > 0

    @property
    def vencido(self):
        """Verifica se está vencido"""
        dias = self.dias_para_vencer
        return dias is not None and dias <= 0


class CampanhaValidadeAutomatica(BaseTenantModel):
    """Configuracao da campanha automatica por validade."""

    __tablename__ = "campanha_validade_automatica"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    ativo = Column(Boolean, nullable=False, default=False)
    aplicar_app = Column(Boolean, nullable=False, default=True)
    aplicar_ecommerce = Column(Boolean, nullable=False, default=True)
    desconto_60_dias = Column(Float, nullable=False, default=10)
    desconto_30_dias = Column(Float, nullable=False, default=20)
    desconto_7_dias = Column(Float, nullable=False, default=35)
    rotulo_publico = Column(String(80), nullable=True)
    mensagem_publica = Column(Text, nullable=True)


class CampanhaValidadeExclusao(BaseTenantModel):
    """Opt-out manual da campanha automatica por produto ou lote."""

    __tablename__ = "campanha_validade_exclusoes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    produto_id = Column(
        Integer,
        ForeignKey("produtos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lote_id = Column(
        Integer,
        ForeignKey("produto_lotes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ativo = Column(Boolean, nullable=False, default=True)
    motivo = Column(String(120), nullable=True)
    observacao = Column(Text, nullable=True)

    produto = relationship("Produto")
    lote = relationship("ProdutoLote")


class ProdutoFornecedor(BaseTenantModel):
    """Fornecedores alternativos do produto"""

    __tablename__ = "produto_fornecedores"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    produto_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False
    )
    fornecedor_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    codigo_fornecedor = Column(String(50), nullable=True)
    preco_custo = Column(Float, nullable=True)
    prazo_entrega = Column(Integer, nullable=True)  # dias
    estoque_fornecedor = Column(Float, nullable=True)
    e_principal = Column(Boolean, default=False)

    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    produto = relationship("Produto", back_populates="fornecedores_alternativos")
    fornecedor = relationship("Cliente")


class ListaPreco(BaseTenantModel):
    """Listas de preço (atacado, varejo, VIP, etc)"""

    __tablename__ = "listas_preco"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    produtos = relationship("ProdutoListaPreco", back_populates="lista_preco")
    user = relationship("User")


class ProdutoListaPreco(BaseTenantModel):
    """Preços por lista"""

    __tablename__ = "produto_listas_preco"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    produto_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False
    )
    lista_preco_id = Column(
        Integer, ForeignKey("listas_preco.id", ondelete="CASCADE"), nullable=False
    )
    preco = Column(Float, nullable=False)
    desconto_percentual = Column(Float, nullable=True)
    desconto_valor = Column(Float, nullable=True)
    ativo = Column(Boolean, default=True)

    # Relationships
    produto = relationship("Produto", back_populates="listas_preco")
    lista_preco = relationship("ListaPreco", back_populates="produtos")


class EstoqueMovimentacao(BaseTenantModel):
    """Movimentações de estoque com rastreamento de lotes"""

    __tablename__ = "estoque_movimentacoes"
    __table_args__ = (
        Index(
            "ix_estoque_mov_tenant_produto_created",
            "tenant_id",
            "produto_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_estoque_mov_tenant_documento_motivo",
            "tenant_id",
            "documento",
            "motivo",
        ),
        Index(
            "ix_estoque_mov_tenant_motivo_created",
            "tenant_id",
            "motivo",
            "created_at",
            "id",
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    tipo = Column(String(20), nullable=False)  # entrada, saida, transferencia
    motivo = Column(
        String(80), nullable=True
    )  # compra, venda, ajuste, devolucao, perda, transferencia, balanco

    quantidade = Column(Float, nullable=False)
    quantidade_anterior = Column(Float, nullable=True)
    quantidade_nova = Column(Float, nullable=True)

    custo_unitario = Column(Float, nullable=True)
    valor_total = Column(Float, nullable=True)

    # Lotes
    lote_id = Column(
        Integer, ForeignKey("produto_lotes.id"), nullable=True
    )  # Lote principal (para entradas)
    lotes_consumidos = Column(
        Text, nullable=True
    )  # JSON: [{"lote_id": 1, "quantidade": 5}]

    # Origem/Destino
    estoque_origem = Column(String(20), nullable=True)  # fisico, ecommerce
    estoque_destino = Column(String(20), nullable=True)

    # Referências
    documento = Column(String(50), nullable=True)  # Número NFe, número venda, etc
    referencia_id = Column(Integer, nullable=True)  # ID da venda, compra, etc
    referencia_tipo = Column(
        String(50), nullable=True
    )  # venda, compra, ajuste, procedimento_veterinario

    # Status da movimentação
    # reservado: estoque baixado mas pendente de confirmação (venda em aberto)
    # confirmado: estoque definitivamente baixado (NF emitida e autorizada)
    # cancelado: movimentação cancelada (devolução, cancelamento)
    status = Column(
        String(20), default="confirmado", nullable=False
    )  # reservado, confirmado, cancelado

    observacao = Column(Text, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    produto = relationship("Produto", back_populates="movimentacoes")
    lote = relationship("ProdutoLote")
    user = relationship("User")


class ProdutoBlingSync(BaseTenantModel):
    """Sincroniza��o de produtos com Bling"""

    __tablename__ = "produto_bling_sync"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, unique=True)
    bling_produto_id = Column(String(50), nullable=True)
    sincronizar = Column(Boolean, default=True)
    estoque_compartilhado = Column(Boolean, default=True)
    ultima_sincronizacao = Column(DateTime, nullable=True)
    ultima_conferencia_bling = Column(DateTime, nullable=True)
    ultima_tentativa_sync = Column(DateTime, nullable=True)
    proxima_tentativa_sync = Column(DateTime, nullable=True)
    ultima_sincronizacao_sucesso = Column(DateTime, nullable=True)
    tentativas_sync = Column(Integer, default=0)
    ultimo_estoque_bling = Column(Float, nullable=True)
    ultima_divergencia = Column(Float, nullable=True)
    status = Column(String(20), default="ativo")  # ativo, pausado, erro
    erro_mensagem = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    produto = relationship("Produto", back_populates="bling_sync")
    fila = relationship(
        "ProdutoBlingSyncQueue", back_populates="sync", cascade="all, delete-orphan"
    )


class ProdutoBlingSyncQueue(BaseTenantModel):
    """Fila persistente de sincronização de estoque com o Bling."""

    __tablename__ = "produto_bling_sync_queue"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    sync_id = Column(
        Integer, ForeignKey("produto_bling_sync.id"), nullable=False, index=True
    )
    estoque_novo = Column(Float, nullable=False)
    motivo = Column(String(80), nullable=True)
    origem = Column(String(30), nullable=True)
    status = Column(
        String(20), default="pendente", nullable=False
    )  # pendente, processando, sucesso, erro, falha_final
    forcar_sync = Column(Boolean, default=False, nullable=False)
    tentativas = Column(Integer, default=0, nullable=False)
    ultima_tentativa_em = Column(DateTime, nullable=True)
    proxima_tentativa_em = Column(DateTime, nullable=True)
    processado_em = Column(DateTime, nullable=True)
    ultimo_erro = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    produto = relationship("Produto", back_populates="bling_sync_queue_items")
    sync = relationship("ProdutoBlingSync", back_populates="fila")
