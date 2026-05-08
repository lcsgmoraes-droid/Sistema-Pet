from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from app.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class DataSubjectRequest(Base):
    """Operational request made by a data subject or on their behalf."""

    __tablename__ = "data_subject_requests"
    __table_args__ = (
        Index("ix_data_subject_requests_tenant_status", "tenant_id", "status"),
        Index("ix_data_subject_requests_subject", "tenant_id", "subject_type", "subject_id"),
        Index("ix_data_subject_requests_type", "request_type"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False)

    subject_type = Column(String(50), nullable=False)  # customer, user, contact
    subject_id = Column(String(255), nullable=False)
    request_type = Column(String(50), nullable=False)  # access, export, correction, deletion, revoke, info
    status = Column(String(30), nullable=False, default="pending")

    requester_name = Column(String(255), nullable=True)
    requester_email = Column(String(255), nullable=True)
    requester_phone = Column(String(50), nullable=True)
    channel = Column(String(50), nullable=True)

    details = Column(Text, nullable=True)
    request_payload = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_by_user_id = Column(Integer, nullable=True)
    processed_by_user_id = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    due_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
