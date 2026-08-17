"""Pedidos e eventos recebidos da iFood Merchant API."""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class IfoodOrder(BaseTenantModel):
    """Espelho operacional do pedido iFood dentro de uma empresa CorePet."""

    __tablename__ = "ifood_orders"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ifood_order_id",
            name="uq_ifood_orders_tenant_order",
        ),
        Index("ix_ifood_orders_tenant_status", "tenant_id", "status"),
        Index("ix_ifood_orders_merchant_id", "tenant_id", "merchant_id"),
    )

    merchant_id = Column(String(36), nullable=False)
    ifood_order_id = Column(String(64), nullable=False)
    display_id = Column(String(64), nullable=True)
    status = Column(String(64), nullable=False, default="PLACED")
    order_type = Column(String(32), nullable=True)
    order_timing = Column(String(32), nullable=True)
    delivered_by = Column(String(32), nullable=True)
    total = Column(Float, nullable=True)
    placed_at = Column(DateTime(timezone=True), nullable=True)
    preparation_start_at = Column(DateTime(timezone=True), nullable=True)
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    last_action = Column(String(64), nullable=True)
    last_action_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)


class IfoodEvent(BaseTenantModel):
    """Evento persistido antes do acknowledgment para garantir idempotencia."""

    __tablename__ = "ifood_events"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "ifood_event_id",
            name="uq_ifood_events_tenant_event",
        ),
        Index("ix_ifood_events_tenant_order", "tenant_id", "ifood_order_id"),
        Index("ix_ifood_events_processing", "tenant_id", "processed_at"),
    )

    merchant_id = Column(String(36), nullable=False)
    ifood_event_id = Column(String(64), nullable=False)
    ifood_order_id = Column(String(64), nullable=True)
    code = Column(String(64), nullable=True)
    full_code = Column(String(128), nullable=True)
    provider_created_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
