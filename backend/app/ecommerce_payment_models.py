"""Modelos de configuracao de pagamento do e-commerce por tenant."""

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text, UniqueConstraint

from app.base_models import BaseTenantModel


class EcommercePaymentGatewayConfig(BaseTenantModel):
    """Credenciais e status de gateway de pagamento para uma loja/tenant."""

    __tablename__ = "ecommerce_payment_gateway_configs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            name="uq_ecommerce_payment_gateway_tenant_provider",
        ),
        Index("ix_ecommerce_payment_gateway_tenant_enabled", "tenant_id", "enabled"),
    )

    provider = Column(String(50), nullable=False, server_default="mercadopago")
    enabled = Column(Boolean, nullable=False, server_default="false")
    environment = Column(String(20), nullable=False, server_default="production")
    public_key = Column(Text, nullable=True)
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    access_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    webhook_secret_encrypted = Column(Text, nullable=True)
    webhook_token = Column(String(80), nullable=False, unique=True, index=True)
    oauth_connected = Column(Boolean, nullable=False, server_default="false")
    oauth_connected_at = Column(DateTime(timezone=True), nullable=True)
    mercado_pago_user_id = Column(String(80), nullable=True)
    oauth_scope = Column(Text, nullable=True)
    oauth_last_error = Column(Text, nullable=True)
    oauth_refresh_failed_at = Column(DateTime(timezone=True), nullable=True)
