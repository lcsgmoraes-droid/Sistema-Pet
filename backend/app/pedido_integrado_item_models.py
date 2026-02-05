
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.database.base import BaseTenantModel
from datetime import datetime

class PedidoIntegradoItem(BaseTenantModel):
    """
    Item de pedido integrado.
    Responsável pela reserva de estoque.
    """
    __tablename__ = "pedidos_integrados_itens"

    pedido_integrado_id = Column(
        String,
        ForeignKey("pedidos_integrados.id"),
        nullable=False,
        index=True
    )

    sku = Column(String(100), nullable=False, index=True)
    descricao = Column(String(255), nullable=True)

    quantidade = Column(Integer, nullable=False)

    reservado_em = Column(DateTime, default=datetime.utcnow)
    liberado_em = Column(DateTime, nullable=True)
    vendido_em = Column(DateTime, nullable=True)
