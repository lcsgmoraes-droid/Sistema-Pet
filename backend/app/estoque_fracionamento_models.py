"""Modelos de conversao de produto fechado para estoque clinico fracionado."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base_models import BaseTenantModel


class EstoqueFracionamentoVinculo(BaseTenantModel):
    """Regra reutilizavel de conversao entre um produto fechado e um clinico."""

    __tablename__ = "estoque_fracionamento_vinculos"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "produto_origem_id",
            "produto_destino_id",
            name="uq_estoque_fracionamento_origem_destino",
        ),
        Index(
            "ix_estoque_fracionamento_vinculo_origem",
            "tenant_id",
            "produto_origem_id",
        ),
        Index(
            "ix_estoque_fracionamento_vinculo_destino",
            "tenant_id",
            "produto_destino_id",
        ),
    )

    produto_origem_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False
    )
    produto_destino_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False
    )
    fator_conversao = Column(Float, nullable=False)
    validade_apos_abertura_dias = Column(Integer, nullable=True)
    observacao = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    produto_origem = relationship("Produto", foreign_keys=[produto_origem_id])
    produto_destino = relationship("Produto", foreign_keys=[produto_destino_id])
    user = relationship("User")


class EstoqueFracionamentoConversao(BaseTenantModel):
    """Evento auditavel de abertura/fracionamento de estoque clinico."""

    __tablename__ = "estoque_fracionamento_conversoes"
    __table_args__ = (
        Index(
            "ix_estoque_fracionamento_conversao_created",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_estoque_fracionamento_conversao_origem",
            "tenant_id",
            "produto_origem_id",
        ),
        Index(
            "ix_estoque_fracionamento_conversao_destino",
            "tenant_id",
            "produto_destino_id",
        ),
    )

    vinculo_id = Column(
        Integer,
        ForeignKey("estoque_fracionamento_vinculos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    produto_origem_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False
    )
    produto_destino_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False
    )
    quantidade_origem = Column(Float, nullable=False)
    fator_conversao = Column(Float, nullable=False)
    quantidade_destino = Column(Float, nullable=False)
    unidade_origem = Column(String(10), nullable=False)
    unidade_destino = Column(String(10), nullable=False)
    estoque_origem_anterior = Column(Float, nullable=False)
    estoque_origem_novo = Column(Float, nullable=False)
    estoque_destino_anterior = Column(Float, nullable=False)
    estoque_destino_novo = Column(Float, nullable=False)
    custo_origem_unitario = Column(Float, nullable=False, default=0)
    custo_destino_unitario = Column(Float, nullable=False, default=0)
    lotes_origem_consumidos = Column(JSON, nullable=True)
    lotes_destino_criados = Column(JSON, nullable=True)
    aberto_em = Column(DateTime(timezone=True), nullable=False)
    validade_apos_abertura_em = Column(DateTime(timezone=True), nullable=True)
    documento = Column(String(50), nullable=True)
    observacao = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="confirmado")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    vinculo = relationship("EstoqueFracionamentoVinculo")
    produto_origem = relationship("Produto", foreign_keys=[produto_origem_id])
    produto_destino = relationship("Produto", foreign_keys=[produto_destino_id])
    user = relationship("User")
