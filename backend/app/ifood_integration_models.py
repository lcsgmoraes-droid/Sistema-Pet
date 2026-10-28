"""Configuracao multiempresa da integracao CorePet com o iFood."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class IfoodMerchantConfig(BaseTenantModel):
    """Vinculo de uma empresa CorePet a uma loja (merchant) do iFood.

    As credenciais OAuth pertencem ao aplicativo CorePet e ficam somente nas
    variaveis de ambiente do servidor. Esta tabela guarda apenas configuracoes
    operacionais da empresa.
    """

    __tablename__ = "ifood_merchant_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_ifood_merchant_configs_tenant"),
        Index("ix_ifood_merchant_configs_status", "tenant_id", "status"),
    )

    merchant_id = Column(String(36), nullable=True)
    active = Column(Boolean, nullable=False, default=False)
    catalog_source = Column(String(20), nullable=False, default="ecommerce")
    default_markup_percent = Column(Float, nullable=False, default=0)
    stock_safety = Column(Float, nullable=False, default=0)
    # NULL significa desconhecido. Zero precisa ser informado explicitamente.
    commission_merchant_percent = Column(Float, nullable=True)
    commission_ifood_percent = Column(Float, nullable=True)
    payment_fee_percent = Column(Float, nullable=True)
    tax_percent = Column(Float, nullable=True)
    additional_unit_cost = Column(Float, nullable=True)
    target_margin_percent = Column(Float, nullable=True)
    # Proveniencia declarada pela loja; nunca preenchida a partir de medias
    # dos pedidos nem confundida com validacao automatica do contrato pelo iFood.
    rates_reference = Column(String(240), nullable=True)
    rates_valid_from = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    last_connection_check_at = Column(DateTime(timezone=True), nullable=True)
    last_catalog_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_orders_poll_at = Column(DateTime(timezone=True), nullable=True)
    last_orders_error = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)


class IfoodMarginRulesRevision(BaseTenantModel):
    """Historico das premissas locais, independente das cobrancas do provedor."""

    __tablename__ = "ifood_margin_rules_revisions"
    merchant_id = Column(String(36), nullable=True)
    actor_id = Column(Integer, nullable=False)
    # Numeros serializados como strings decimais; ausencia preservada como NULL.
    values = Column(JSON, nullable=False)
