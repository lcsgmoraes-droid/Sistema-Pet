
from sqlalchemy import Column, String, DateTime, JSON
from app.database.base import BaseTenantModel
from datetime import datetime, timedelta

class PedidoIntegrado(BaseTenantModel):
    """
    Pedido vindo de integração (ex: Bling).
    Fonte da verdade para reserva de estoque.
    """
    __tablename__ = "pedidos_integrados"

    # Identificação Bling
    pedido_bling_id = Column(String(50), nullable=False, index=True)
    pedido_bling_numero = Column(String(50), nullable=True)

    canal = Column(String(50), nullable=False)

    status = Column(String(30), default="aberto")
    # aberto | confirmado | expirado | cancelado

    criado_em = Column(DateTime, default=datetime.utcnow)
    expira_em = Column(DateTime, nullable=False)

    confirmado_em = Column(DateTime, nullable=True)
    cancelado_em = Column(DateTime, nullable=True)

    # Payload completo do Bling (para uso futuro)
    payload = Column(JSON, nullable=False)

    @staticmethod
    def calcular_expiracao(horas=48):
        return datetime.utcnow() + timedelta(hours=horas)
