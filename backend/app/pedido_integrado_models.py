from sqlalchemy import Column, String, DateTime, JSON, UniqueConstraint
from app.base_models import BaseTenantModel
from datetime import datetime, timedelta


class PedidoIntegrado(BaseTenantModel):
    """
    Pedido vindo de integração (ex: Bling).
    Fonte da verdade para reserva de estoque.
    """

    __tablename__ = "pedidos_integrados"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_pedidos_integrados_tenant_id"),
    )

    # Identificação Bling
    # Outras origens (por exemplo iFood) nao inventam identificadores Bling.
    pedido_bling_id = Column(String(50), nullable=True, index=True)
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
    def calcular_expiracao(dias=15):
        return datetime.utcnow() + timedelta(days=dias)
