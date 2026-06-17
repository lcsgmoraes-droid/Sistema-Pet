from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class OpsErrorEvent(Base):
    __tablename__ = "ops_error_events"
    __table_args__ = (
        Index("ix_ops_error_events_tenant_created", "tenant_id", "created_at"),
        Index("ix_ops_error_events_path_created", "path", "created_at"),
        Index("ix_ops_error_events_status_created", "status_code", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_key = Column(String(96), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    captured_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(String(80), nullable=True)
    user_email = Column(String(255), nullable=True)
    request_id = Column(String(80), nullable=True, index=True)
    method = Column(String(12), nullable=True)
    path = Column(String(600), nullable=True, index=True)
    status_code = Column(Integer, nullable=True, index=True)
    duration_ms = Column(Float, nullable=False, default=0)
    exception_type = Column(String(160), nullable=True)
    exception_message = Column(Text, nullable=True)
    client_ip = Column(String(80), nullable=True)
    user_agent = Column(String(300), nullable=True)
    source = Column(String(60), nullable=False, default="request_context")
    payload = Column(JSON, nullable=True)


class OpsAlert(Base):
    __tablename__ = "ops_alerts"
    __table_args__ = (
        Index("ix_ops_alerts_status_severity", "status", "severity"),
        Index("ix_ops_alerts_tenant_status", "tenant_id", "status"),
        Index("ix_ops_alerts_last_seen", "last_seen_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    alert_key = Column(String(180), nullable=False, unique=True, index=True)
    scope = Column(String(40), nullable=False, index=True)
    kind = Column(String(80), nullable=False, index=True)
    severity = Column(String(24), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="open", index=True)
    title = Column(String(255), nullable=False)
    detail = Column(Text, nullable=True)
    action = Column(Text, nullable=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    tenant_name = Column(String(255), nullable=True)
    path = Column(String(600), nullable=True, index=True)
    request_id = Column(String(80), nullable=True, index=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, index=True)
    latest_event_at = Column(DateTime(timezone=True), nullable=True)
    occurrence_count = Column(Integer, nullable=False, default=1)
    score = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class OpsRecoveryAction(Base):
    __tablename__ = "ops_recovery_actions"
    __table_args__ = (
        Index("ix_ops_recovery_actions_type_created", "action_type", "created_at"),
        Index("ix_ops_recovery_actions_status_created", "status", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    action_key = Column(String(160), nullable=False, unique=True, index=True)
    action_type = Column(String(80), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    source_event_type = Column(String(80), nullable=True, index=True)
    message = Column(Text, nullable=True)
    pid = Column(Integer, nullable=True)
    uvicorn_pid = Column(Integer, nullable=True)
    hostname = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    captured_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload = Column(JSON, nullable=True)
