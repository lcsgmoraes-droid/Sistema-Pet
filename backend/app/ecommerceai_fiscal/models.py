"""Identidade permanente, consentimento e envio fiscal de pedidos externos."""

from sqlalchemy import Column, String, Integer, JSON, DateTime, Boolean, LargeBinary
from sqlalchemy import (
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    Index,
    CheckConstraint,
)
from app.base_models import BaseTenantModel


class FiscalAccount(BaseTenantModel):
    __tablename__ = "ecommerceai_fiscal_accounts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "channel", "seller_id", name="uq_eai_fiscal_seller"
        ),
        UniqueConstraint("tenant_id", "id", name="uq_eai_fiscal_account_tenant"),
        CheckConstraint(
            "discount_policy IN ('source_discounts','buyer_payment_total')",
            name="ck_eai_fiscal_policy",
        ),
        CheckConstraint("channel = 'amazon'", name="ck_eai_fiscal_channel"),
    )
    channel = Column(String(20), nullable=False)
    seller_id = Column(String(80), nullable=False)
    marketplace_id = Column(String(80), nullable=False)
    emitter_cnpj = Column(String(14), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    auto_issue_enabled = Column(Boolean, nullable=False, default=False)
    activated_at = Column(DateTime(timezone=True))
    discount_policy = Column(String(40), nullable=False, default="source_discounts")
    approved_by_user_id = Column(Integer, nullable=False)


class FiscalSkuMapping(BaseTenantModel):
    __tablename__ = "ecommerceai_fiscal_sku_mappings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "account_id"],
            ["ecommerceai_fiscal_accounts.tenant_id", "ecommerceai_fiscal_accounts.id"],
        ),
        UniqueConstraint(
            "tenant_id", "account_id", "seller_sku", name="uq_eai_fiscal_sku"
        ),
    )
    account_id = Column(Integer, nullable=False)
    seller_sku = Column(String(100), nullable=False)
    product_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    approved_by_user_id = Column(Integer, nullable=False)


class ExternalFiscalOrder(BaseTenantModel):
    __tablename__ = "ecommerceai_fiscal_orders"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "account_id"],
            ["ecommerceai_fiscal_accounts.tenant_id", "ecommerceai_fiscal_accounts.id"],
        ),
        UniqueConstraint(
            "tenant_id",
            "channel",
            "seller_id",
            "external_order_id",
            name="uq_eai_fiscal_order_identity",
        ),
        UniqueConstraint("idempotency_key", name="uq_eai_fiscal_idempotency"),
        Index("ix_eai_fiscal_order_queue", "tenant_id", "status", "lease_until"),
        CheckConstraint("source_revision > 0", name="ck_eai_fiscal_revision"),
        CheckConstraint(
            "status IN ('blocked','ready','processing','unknown','authorized','rejected','canceled')",
            name="ck_eai_fiscal_status",
        ),
    )
    account_id = Column(Integer, nullable=True)
    connection_id = Column(
        Integer, ForeignKey("ecommerceai_connections.id"), nullable=False
    )
    channel = Column(String(20), nullable=False)
    seller_id = Column(String(80), nullable=False)
    external_order_id = Column(String(80), nullable=False)
    source_revision = Column(Integer, nullable=False)
    source_hash = Column(String(64), nullable=False)
    source = Column(JSON, nullable=False)
    purchased_at = Column(DateTime(timezone=True), nullable=False)
    historical_reviewed_at = Column(DateTime(timezone=True))
    reviewed_by_user_id = Column(Integer)
    payload = Column(JSON)
    payload_hash = Column(String(64))
    discount_audit = Column(JSON)
    status = Column(String(20), nullable=False, default="blocked")
    blockers = Column(JSON, nullable=False, default=list)
    idempotency_key = Column(String(128))
    submitted_at = Column(DateTime(timezone=True))
    lease_token = Column(String(36))
    lease_until = Column(DateTime(timezone=True))
    correlation_id = Column(String(128))
    numero = Column(String(20))
    chave = Column(String(44))
    protocolo = Column(String(128))
    xml = Column(LargeBinary)
    xml_sha256 = Column(String(64))
