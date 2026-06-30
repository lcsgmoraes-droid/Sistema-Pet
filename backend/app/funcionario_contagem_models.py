# -*- coding: utf-8 -*-
"""Modelos da contagem avulsa feita pelo app do funcionario."""

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from .base_models import BaseTenantModel


class FuncionarioContagem(BaseTenantModel):
    """Cabecalho da contagem salva pelo funcionario."""

    __tablename__ = "funcionario_contagens"
    __table_args__ = (
        Index("ix_funcionario_contagens_tenant_created", "tenant_id", "created_at"),
        Index(
            "ix_funcionario_contagens_tenant_funcionario", "tenant_id", "funcionario_id"
        ),
        Index(
            "ix_funcionario_contagens_tenant_fornecedor", "tenant_id", "fornecedor_id"
        ),
        {"extend_existing": True},
    )

    funcionario_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    fornecedor_nome_snapshot = Column(String(255), nullable=True)
    titulo = Column(String(160), nullable=False, default="Contagem")
    observacao = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="salva")

    funcionario = relationship("Cliente", foreign_keys=[funcionario_id])
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
    user = relationship("User")
    itens = relationship(
        "FuncionarioContagemItem",
        back_populates="contagem",
        cascade="all, delete-orphan",
        order_by="FuncionarioContagemItem.ordem",
    )


class FuncionarioContagemItem(BaseTenantModel):
    """Item contado, com snapshot do produto no momento da contagem."""

    __tablename__ = "funcionario_contagem_itens"
    __table_args__ = (
        Index(
            "ix_funcionario_contagem_itens_tenant_contagem", "tenant_id", "contagem_id"
        ),
        Index(
            "ix_funcionario_contagem_itens_tenant_produto", "tenant_id", "produto_id"
        ),
        {"extend_existing": True},
    )

    contagem_id = Column(
        Integer,
        ForeignKey("funcionario_contagens.id", ondelete="CASCADE"),
        nullable=False,
    )
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    ordem = Column(Integer, nullable=False, default=0)
    codigo = Column(String(50), nullable=True)
    codigo_barras = Column(String(50), nullable=True)
    gtin_ean = Column(String(50), nullable=True)
    nome = Column(String(255), nullable=False)
    unidade = Column(String(20), nullable=False, default="UN")
    quantidade = Column(Float, nullable=False, default=0)
    preco_custo_snapshot = Column(Numeric(12, 2), nullable=False, default=0)
    preco_venda_snapshot = Column(Numeric(12, 2), nullable=False, default=0)
    observacao = Column(Text, nullable=True)

    contagem = relationship("FuncionarioContagem", back_populates="itens")
    produto = relationship("Produto")
