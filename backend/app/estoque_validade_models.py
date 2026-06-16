from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class EstoqueValidadeBloqueio(BaseTenantModel):
    """Bloqueio operacional de lote retirado do estoque vendavel por validade."""

    __tablename__ = "estoque_validade_bloqueios"
    __table_args__ = (
        Index("ix_estoque_validade_tenant_status", "tenant_id", "status"),
        Index("ix_estoque_validade_tenant_produto", "tenant_id", "produto_id"),
        Index("ix_estoque_validade_tenant_lote", "tenant_id", "lote_id"),
        Index("ix_estoque_validade_lote_status", "lote_id", "status"),
        {"extend_existing": True},
    )

    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    lote_id = Column(
        Integer, ForeignKey("produto_lotes.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    status = Column(String(30), nullable=False, default="pendente")
    origem = Column(String(30), nullable=False, default="rotina")
    data_referencia = Column(DateTime(timezone=True), nullable=False)
    data_validade = Column(DateTime(timezone=True), nullable=True)

    quantidade_bloqueada = Column(Float, nullable=False, default=0)
    quantidade_resolvida = Column(Float, nullable=False, default=0)
    custo_unitario = Column(Float, nullable=True)
    custo_total_estimado = Column(Float, nullable=False, default=0)

    movimentacao_bloqueio_id = Column(
        Integer, ForeignKey("estoque_movimentacoes.id"), nullable=True
    )
    movimentacao_resolucao_id = Column(
        Integer, ForeignKey("estoque_movimentacoes.id"), nullable=True
    )

    decidido_por_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decidido_em = Column(DateTime(timezone=True), nullable=True)
    decisao = Column(String(30), nullable=True)
    observacao = Column(Text, nullable=True)

    produto = relationship("Produto")
    lote = relationship("ProdutoLote")
