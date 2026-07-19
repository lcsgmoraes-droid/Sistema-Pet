"""Modelos do plano de controle de cobranca do CorePet."""

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db import Base


class BillingWebhookEvent(Base):
    """Recibo idempotente de webhook, sem guardar o payload com dados pessoais."""

    __tablename__ = "billing_webhook_events"
    __table_args__ = (
        UniqueConstraint(
            "provider", "event_id", name="uq_billing_webhook_provider_event"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(30), nullable=False)
    event_id = Column(String(120), nullable=False)
    event_type = Column(String(80), nullable=False)
    tenant_reference = Column(String(36), nullable=True, index=True)
    provider_payment_id = Column(String(80), nullable=True, index=True)
    payload_sha256 = Column(String(64), nullable=False)
    processing_status = Column(String(20), nullable=False, server_default="processing")
    error_message = Column(String(500), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
