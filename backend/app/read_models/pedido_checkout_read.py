from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.db import Base


class PedidoCheckoutRead(Base):
    __tablename__ = "pedido_checkout_read"

    id = Column(Integer, primary_key=True)
    pedido_id = Column(String, index=True)
    cliente_id = Column(Integer)
    tenant_id = Column(String, index=True)

    total = Column(Float)
    items_count = Column(Integer)
    subtotal_items = Column(Float)

    origem = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)