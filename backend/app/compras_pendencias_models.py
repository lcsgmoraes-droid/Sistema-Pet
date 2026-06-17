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


class CompraPendenciaFornecedor(BaseTenantModel):
    """Supplier resolution workflow created from purchase/NF divergences."""

    __tablename__ = "compras_pendencias_fornecedor"
    __table_args__ = (
        Index("ix_compras_pendencias_fornecedor_tenant_status", "tenant_id", "status"),
        Index(
            "ix_compras_pendencias_fornecedor_tenant_nota",
            "tenant_id",
            "nota_entrada_id",
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(40), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="aberta", index=True)
    origem = Column(String(30), nullable=False, default="conferencia_nf")
    tipo = Column(String(40), nullable=False, default="divergencia_fornecedor")

    fornecedor_id = Column(Integer, nullable=True, index=True)
    fornecedor_nome = Column(String(255), nullable=False)
    fornecedor_cnpj = Column(String(18), nullable=True)

    nota_entrada_id = Column(
        Integer, ForeignKey("notas_entrada.id"), nullable=True, index=True
    )
    pedido_compra_id = Column(
        Integer, ForeignKey("pedidos_compra.id"), nullable=True, index=True
    )
    numero_nota = Column(String(20), nullable=True)
    numero_pedido = Column(String(50), nullable=True)

    titulo = Column(String(255), nullable=False)
    resumo = Column(Text, nullable=True)
    prazo_previsto = Column(DateTime, nullable=True)

    email_destinatario = Column(String(255), nullable=True)
    email_assunto = Column(String(255), nullable=True)
    email_mensagem = Column(Text, nullable=True)
    email_enviado_em = Column(DateTime, nullable=True)
    pdf_gerado_em = Column(DateTime, nullable=True)

    resolvida_em = Column(DateTime, nullable=True)
    resolucao_observacao = Column(Text, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    itens = relationship(
        "CompraPendenciaFornecedorItem",
        back_populates="pendencia",
        cascade="all, delete-orphan",
        order_by="CompraPendenciaFornecedorItem.id.asc()",
    )
    historico = relationship(
        "CompraPendenciaFornecedorHistorico",
        back_populates="pendencia",
        cascade="all, delete-orphan",
        order_by="CompraPendenciaFornecedorHistorico.created_at.desc()",
    )
    nota = relationship("NotaEntrada", foreign_keys=[nota_entrada_id])
    pedido = relationship("PedidoCompra", foreign_keys=[pedido_compra_id])
    user = relationship("User", foreign_keys=[user_id])


class CompraPendenciaFornecedorItem(BaseTenantModel):
    """Divergent item attached to a supplier pending resolution."""

    __tablename__ = "compras_pendencias_fornecedor_itens"
    __table_args__ = (
        Index(
            "ix_compras_pendencias_fornecedor_itens_tenant_pendencia",
            "tenant_id",
            "pendencia_id",
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    pendencia_id = Column(
        Integer,
        ForeignKey("compras_pendencias_fornecedor.id"),
        nullable=False,
        index=True,
    )
    nota_entrada_item_id = Column(
        Integer, ForeignKey("notas_entrada_itens.id"), nullable=True, index=True
    )
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=True, index=True)

    codigo_produto = Column(String(100), nullable=True)
    descricao = Column(String(500), nullable=False)
    unidade = Column(String(10), nullable=True)

    quantidade_nf = Column(Float, nullable=False, default=0)
    quantidade_recebida = Column(Float, nullable=False, default=0)
    quantidade_faltante = Column(Float, nullable=False, default=0)
    quantidade_avariada = Column(Float, nullable=False, default=0)
    valor_unitario = Column(Float, nullable=False, default=0)
    valor_total_divergente = Column(Float, nullable=False, default=0)

    status_conferencia = Column(String(30), nullable=False, default="falta")
    acao_sugerida = Column(String(40), nullable=False, default="contatar_fornecedor")
    observacao = Column(Text, nullable=True)
    resolvido = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pendencia = relationship("CompraPendenciaFornecedor", back_populates="itens")
    nota_item = relationship("NotaEntradaItem", foreign_keys=[nota_entrada_item_id])
    produto = relationship("Produto", foreign_keys=[produto_id])


class CompraPendenciaFornecedorHistorico(BaseTenantModel):
    """Timeline for supplier pending resolution."""

    __tablename__ = "compras_pendencias_fornecedor_historico"
    __table_args__ = (
        Index(
            "ix_compras_pendencias_fornecedor_hist_tenant_pendencia",
            "tenant_id",
            "pendencia_id",
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    pendencia_id = Column(
        Integer,
        ForeignKey("compras_pendencias_fornecedor.id"),
        nullable=False,
        index=True,
    )
    tipo = Column(String(40), nullable=False)
    observacao = Column(Text, nullable=True)
    status_anterior = Column(String(30), nullable=True)
    status_novo = Column(String(30), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pendencia = relationship("CompraPendenciaFornecedor", back_populates="historico")
    user = relationship("User", foreign_keys=[user_id])
