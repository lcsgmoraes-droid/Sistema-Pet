from sqlalchemy import Column, Integer, Float, DateTime
from app.db.base_class import Base
from datetime import datetime

class PedidoDashboardRead(Base):
    __tablename__ = "pedido_dashboard_read"

    id = Column(Integer, primary_key=True, index=True)

    total_pedidos = Column(Integer, default=0)
    total_vendas = Column(Float, default=0)
    total_itens = Column(Integer, default=0)
    ticket_medio = Column(Float, default=0)

    updated_at = Column(DateTime, default=datetime.utcnow)
