from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, Index

from app.base_models import BaseTenantModel


class BlingFlowEvent(BaseTenantModel):
    __tablename__ = "bling_flow_events"
    __table_args__ = (
        Index("ix_bling_flow_events_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_bling_flow_events_pedido_bling_id", "pedido_bling_id"),
        Index("ix_bling_flow_events_nf_bling_id", "nf_bling_id"),
        Index("ix_bling_flow_events_event_type", "event_type"),
    )

    source = Column(String(30), nullable=False, default="runtime")
    event_type = Column(String(80), nullable=False)
    entity_type = Column(String(30), nullable=False, default="pedido")
    status = Column(String(20), nullable=False, default="ok")
    severity = Column(String(20), nullable=False, default="info")

    message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    pedido_integrado_id = Column(Integer, nullable=True, index=True)
    pedido_bling_id = Column(String(50), nullable=True)
    nf_bling_id = Column(String(50), nullable=True)
    sku = Column(String(100), nullable=True)

    auto_fix_applied = Column(Boolean, nullable=False, default=False)
    payload = Column(JSON, nullable=True)
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class BlingFlowIncident(BaseTenantModel):
    __tablename__ = "bling_flow_incidents"
    __table_args__ = (
        Index("ix_bling_flow_incidents_tenant_status", "tenant_id", "status"),
        Index("ix_bling_flow_incidents_code", "code"),
        Index("ix_bling_flow_incidents_dedupe_key", "dedupe_key"),
        Index("ix_bling_flow_incidents_pedido_bling_id", "pedido_bling_id"),
    )

    code = Column(String(80), nullable=False)
    severity = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="open")
    source = Column(String(30), nullable=False, default="auditoria")
    scope = Column(String(30), nullable=False, default="pedido")

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    suggested_action = Column(String(255), nullable=True)
    auto_fixable = Column(Boolean, nullable=False, default=False)
    auto_fix_status = Column(String(20), nullable=False, default="pending")

    dedupe_key = Column(String(255), nullable=False)

    pedido_integrado_id = Column(Integer, nullable=True, index=True)
    pedido_bling_id = Column(String(50), nullable=True)
    nf_bling_id = Column(String(50), nullable=True)
    sku = Column(String(100), nullable=True)

    details = Column(JSON, nullable=True)
    first_seen_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_em = Column(DateTime, nullable=True)
    occurrences = Column(Integer, nullable=False, default=1)
