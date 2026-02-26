from dataclasses import dataclass
from app.domain.events.base_event import BaseDomainEvent


@dataclass(frozen=True, kw_only=True)
class PedidoCriadoEvent(BaseDomainEvent):
    pedido_id: str
    cliente_id: int
    total: float
    origem: str  # web | app | marketplace
    tenant_id: str | None = None
    items_count: int = 0
    subtotal_items: float = 0.0