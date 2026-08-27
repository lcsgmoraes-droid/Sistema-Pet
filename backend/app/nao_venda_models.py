"""Modelos do registro rápido de atendimentos que não viraram venda."""

from sqlalchemy import Boolean, Column, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class NaoVenda(BaseTenantModel):
    """Um atendimento no qual o cliente saiu sem concluir a compra."""

    __tablename__ = "nao_vendas"

    cliente_id = Column(
        ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    usuario_registrou_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cliente_nome = Column(String(255), nullable=True)
    cliente_telefone = Column(String(50), nullable=True)
    motivo = Column(String(40), nullable=False, index=True)
    observacoes = Column(Text, nullable=True)
    valor_estimado_total = Column(Numeric(12, 2), nullable=True)
    origem = Column(String(30), nullable=False, default="pdv", server_default="pdv")

    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    usuario_registrou = relationship("User", foreign_keys=[usuario_registrou_id])
    itens = relationship(
        "NaoVendaItem",
        back_populates="nao_venda",
        cascade="all, delete-orphan",
        order_by="NaoVendaItem.id",
    )


class NaoVendaItem(BaseTenantModel):
    """Produto procurado, cadastrado no catálogo ou informado livremente."""

    __tablename__ = "nao_venda_itens"

    nao_venda_id = Column(
        ForeignKey("nao_vendas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    produto_id = Column(
        ForeignKey("produtos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    marca_id = Column(
        ForeignKey("marcas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fornecedor_id = Column(
        ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True
    )

    produto_nome = Column(String(200), nullable=False)
    sku = Column(String(50), nullable=True)
    marca_nome = Column(String(100), nullable=True)
    fornecedor_nome = Column(String(255), nullable=True)
    quantidade = Column(Numeric(12, 4), nullable=False, default=1, server_default="1")
    valor_unitario_estimado = Column(Numeric(12, 2), nullable=True)
    adicionado_lista_espera = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    nao_venda = relationship("NaoVenda", back_populates="itens")
    produto = relationship("Produto", foreign_keys=[produto_id])
    marca = relationship("Marca", foreign_keys=[marca_id])
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
