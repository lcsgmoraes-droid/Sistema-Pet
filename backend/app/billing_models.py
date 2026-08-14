"""Modelos do plano de controle de cobranca do CorePet."""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.base_models import TenantScoped
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


class BillingContractAcceptance(TenantScoped, Base):
    """Comprovante append-only do aceite comercial que originou a cobranca."""

    __tablename__ = "billing_contract_acceptances"
    __table_args__ = (
        UniqueConstraint("acceptance_id", name="uq_billing_contract_acceptance_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    acceptance_id = Column(String(36), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_name = Column(String(255), nullable=True)
    user_email = Column(String(255), nullable=False)
    user_role = Column(String(80), nullable=True)
    contractor_name = Column(String(255), nullable=False)
    contractor_tax_id = Column(String(20), nullable=True)

    contract_version = Column(String(50), nullable=False, index=True)
    terms_version = Column(String(50), nullable=False)
    privacy_version = Column(String(50), nullable=False)
    acceptance_text = Column(Text, nullable=False)
    document_url = Column(String(255), nullable=False)
    terms_url = Column(String(255), nullable=False)
    privacy_url = Column(String(255), nullable=False)
    document_sha256 = Column(String(64), nullable=False)

    plan_code = Column(String(50), nullable=False, index=True)
    plan_name = Column(String(120), nullable=False)
    price_cents = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, server_default="BRL")
    billing_cycle = Column(String(20), nullable=False, server_default="MONTHLY")
    billing_type = Column(String(30), nullable=False)
    first_due_date = Column(Date, nullable=False)
    provider = Column(String(30), nullable=False, server_default="asaas")
    provider_environment = Column(String(20), nullable=False)
    provider_subscription_id = Column(String(80), nullable=False, index=True)

    channel = Column(String(20), nullable=False, server_default="web")
    request_id = Column(String(64), nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    client_timezone = Column(String(80), nullable=True)
    snapshot_json = Column(Text, nullable=False)
    snapshot_sha256 = Column(String(64), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
