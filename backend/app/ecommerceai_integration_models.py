"""Persistencia da integracao bidirecional CorePet <-> EcommerceAI."""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db import Base


JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")
EVENT_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class EcommerceAIConnectionRequest(Base):
    __tablename__ = "ecommerceai_connection_requests"

    id = Column(Integer, primary_key=True)
    request_id = Column(String(36), nullable=False, unique=True, index=True)
    request_nonce = Column(String(80), nullable=False, unique=True)
    client_id = Column(String(80), nullable=False)
    ecommerceai_user_id = Column(String(80), nullable=False, index=True)
    account_name = Column(String(255), nullable=True)
    account_email = Column(String(255), nullable=True)
    callback_url = Column(String(1000), nullable=False)
    state = Column(String(255), nullable=False, unique=True)
    requested_scopes = Column(JSON_DOCUMENT, nullable=False, default=list)
    status = Column(String(32), nullable=False, default="pending", index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    callback_error = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EcommerceAIConnection(Base):
    __tablename__ = "ecommerceai_connections"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_ecommerceai_connections_request"),
        Index(
            "ix_ecommerceai_connections_tenant_status",
            "tenant_id",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), nullable=False, unique=True, index=True)
    request_id = Column(
        String(36),
        ForeignKey("ecommerceai_connection_requests.request_id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    ecommerceai_user_id = Column(String(80), nullable=False, index=True)
    account_name = Column(String(255), nullable=True)
    account_email = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default="callback_pending")
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    token_prefix = Column(String(20), nullable=False)
    scopes = Column(JSON_DOCUMENT, nullable=False, default=list)
    connected_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    last_catalog_read_at = Column(DateTime(timezone=True), nullable=True)
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


class EcommerceAIInboundEvent(Base):
    __tablename__ = "ecommerceai_inbound_events"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "event_id",
            name="uq_ecommerceai_inbound_connection_event",
        ),
        Index(
            "ix_ecommerceai_inbound_tenant_received",
            "tenant_id",
            "received_at",
        ),
        Index(
            "ix_ecommerceai_inbound_tenant_type",
            "tenant_id",
            "event_type",
        ),
    )

    id = Column(EVENT_ID_TYPE, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    connection_id = Column(
        Integer,
        ForeignKey("ecommerceai_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id = Column(String(80), nullable=False)
    event_type = Column(String(120), nullable=False)
    schema_version = Column(String(20), nullable=False, default="1.0")
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    payload = Column(JSON_DOCUMENT, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="received")
    processed_result = Column(JSON_DOCUMENT, nullable=True)
    error_message = Column(Text, nullable=True)
    received_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)
