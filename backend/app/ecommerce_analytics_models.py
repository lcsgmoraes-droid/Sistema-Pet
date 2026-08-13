"""Eventos anônimos do funil da loja virtual."""

from sqlalchemy import Column, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.base_models import BaseTenantModel


class EcommerceAnalyticsEvent(BaseTenantModel):
    __tablename__ = "ecommerce_analytics_events"

    event_name = Column(String(40), nullable=False, index=True)
    session_id = Column(String(80), nullable=False)
    channel = Column(String(20), nullable=False, default="ecommerce")
    path = Column(String(300), nullable=True)
    product_id = Column(Integer, nullable=True)
    pedido_id = Column(String(80), nullable=True)
    value = Column(Float, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    __table_args__ = (
        Index(
            "ix_ecommerce_analytics_tenant_event_created",
            "tenant_id",
            "event_name",
            "created_at",
        ),
        Index(
            "ix_ecommerce_analytics_tenant_session_created",
            "tenant_id",
            "session_id",
            "created_at",
        ),
        Index(
            "ix_ecommerce_analytics_tenant_channel_created",
            "tenant_id",
            "channel",
            "created_at",
        ),
    )
