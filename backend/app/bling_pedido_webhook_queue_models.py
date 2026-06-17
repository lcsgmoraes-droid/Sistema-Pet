from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base_class import Base


class BlingPedidoWebhookEvent(Base):
    """Fila persistente para webhooks de pedidos/NFs recebidos do Bling."""

    __tablename__ = "bling_pedido_webhook_events"
    __table_args__ = (
        Index("ix_bling_pedido_webhook_status_next", "status", "next_attempt_at"),
        Index("ix_bling_pedido_webhook_tenant_status", "tenant_id", "status"),
        Index("ix_bling_pedido_webhook_pedido_status", "pedido_bling_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    dedupe_key = Column(String(96), nullable=False, unique=True, index=True)
    event_id = Column(String(120), nullable=True, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    pedido_bling_id = Column(String(50), nullable=True, index=True)

    status = Column(String(24), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=6)
    next_attempt_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    payload = Column(JSON, nullable=False)
    response_payload = Column(JSON, nullable=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
