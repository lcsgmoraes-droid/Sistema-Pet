"""Vinculos e evidencias locais do piloto Item; aceite nao confirma publicacao."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class IfoodCatalogLink(BaseTenantModel):
    __tablename__ = "ifood_catalog_links"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_ifood_catalog_link_tenant_id"),
        UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "product_id",
            name="uq_ifood_catalog_link_product",
        ),
        UniqueConstraint(
            "tenant_id", "merchant_id", "barcode", name="uq_ifood_catalog_link_barcode"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["produtos.tenant_id", "produtos.id"],
            name="fk_ifood_catalog_link_product",
        ),
        CheckConstraint(
            "mode IN ('existing','new')", name="ck_ifood_catalog_link_mode"
        ),
        CheckConstraint("revision > 0", name="ck_ifood_catalog_link_revision"),
    )
    merchant_id = Column(String(36), nullable=False)
    product_id = Column(Integer, nullable=False)
    barcode = Column(String(13), nullable=False)
    mode = Column(String(12), nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    portal_checked_at = Column(DateTime(timezone=True), nullable=False)
    portal_checked_by = Column(Integer, nullable=False)


class IfoodCatalogConfirmation(BaseTenantModel):
    """Declaracoes humanas append-only; nao substituem respostas da API."""

    __tablename__ = "ifood_catalog_confirmations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "link_id"],
            ["ifood_catalog_links.tenant_id", "ifood_catalog_links.id"],
            name="fk_ifood_catalog_confirmation_link",
        ),
        CheckConstraint(
            "kind IN ('link','portal')", name="ck_ifood_catalog_confirmation_kind"
        ),
        CheckConstraint(
            "price IS NULL OR price >= 0", name="ck_ifood_catalog_confirmation_price"
        ),
        CheckConstraint(
            "stock IS NULL OR stock >= 0", name="ck_ifood_catalog_confirmation_stock"
        ),
    )
    link_id = Column(Integer, nullable=False)
    barcode = Column(String(13), nullable=False)
    kind = Column(String(12), nullable=False)
    present = Column(Boolean, nullable=False)
    portal_active = Column(Boolean, nullable=True)
    price = Column(Numeric(14, 2), nullable=True)
    stock = Column(Numeric(14, 3), nullable=True)
    actor_id = Column(Integer, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=False)


class IfoodCatalogSubmission(BaseTenantModel):
    __tablename__ = "ifood_catalog_submissions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "link_id"],
            ["ifood_catalog_links.tenant_id", "ifood_catalog_links.id"],
            name="fk_ifood_catalog_submission_link",
        ),
        UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "request_key",
            name="uq_ifood_catalog_submission_request",
        ),
        CheckConstraint(
            "operation IN ('create','update')",
            name="ck_ifood_catalog_submission_operation",
        ),
        CheckConstraint(
            "status IN ('sending','accepted','error','uncertain')",
            name="ck_ifood_catalog_submission_status",
        ),
        CheckConstraint(
            "source IN ('manual','auto_stock')",
            name="ck_ifood_catalog_submission_source",
        ),
        CheckConstraint(
            "provider_mode IN ('local_simulator','ifood_api')",
            name="ck_ifood_catalog_submission_provider_mode",
        ),
    )
    link_id = Column(Integer, nullable=False)
    merchant_id = Column(String(36), nullable=False)
    barcode = Column(String(13), nullable=False)
    request_key = Column(String(36), nullable=False)
    operation = Column(String(12), nullable=False)
    source = Column(
        String(16), nullable=False, default="manual", server_default="manual"
    )
    provider_mode = Column(
        String(16), nullable=False, default="ifood_api", server_default="ifood_api"
    )
    fields = Column(JSON, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    # Somente barcode e numeros escolhidos; nunca resposta livre do provedor.
    evidence = Column(JSON, nullable=False)
    status = Column(String(12), nullable=False)
    actor_id = Column(Integer, nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    http_status = Column(Integer, nullable=True)
    provider_request_id = Column(String(36), nullable=True)
    error_code = Column(String(40), nullable=True)


class IfoodStockSyncState(BaseTenantModel):
    """Ultimo saldo desejado do piloto, nunca uma confirmacao remota.

    Cada tentativa continua append-only em IfoodCatalogSubmission. O marcador
    sending e gravado antes da rede: um crash exige conferencia, nao reenvio.
    """

    __tablename__ = "ifood_stock_sync_states"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "merchant_id", "link_id", name="uq_ifood_stock_sync_link"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "link_id"],
            ["ifood_catalog_links.tenant_id", "ifood_catalog_links.id"],
            name="fk_ifood_stock_sync_link",
        ),
        CheckConstraint("link_revision > 0", name="ck_ifood_stock_sync_revision"),
        CheckConstraint(
            "desired_stock IS NULL OR desired_stock >= 0",
            name="ck_ifood_stock_sync_desired",
        ),
        CheckConstraint(
            "last_accepted_stock IS NULL OR last_accepted_stock >= 0",
            name="ck_ifood_stock_sync_accepted",
        ),
        CheckConstraint("failure_count >= 0", name="ck_ifood_stock_sync_failures"),
        CheckConstraint(
            "reference_source IS NULL OR reference_source IN ('portal','api_acceptance')",
            name="ck_ifood_stock_sync_reference",
        ),
        CheckConstraint(
            "status IN ('queued','sending','accepted','backoff','blocked','uncertain')",
            name="ck_ifood_stock_sync_status",
        ),
        CheckConstraint(
            "provider_mode IN ('local_simulator','ifood_api')",
            name="ck_ifood_stock_sync_provider_mode",
        ),
    )
    merchant_id = Column(String(36), nullable=False)
    link_id = Column(Integer, nullable=False)
    provider_mode = Column(
        String(16),
        nullable=False,
        default="local_simulator",
        server_default="local_simulator",
    )
    link_revision = Column(Integer, nullable=False)
    desired_stock = Column(Integer, nullable=True)
    # Ultimo saldo recebido em 202 ou observado no Portal pelo responsavel.
    # Nenhum desses valores comprova que um envio posterior foi aplicado.
    last_accepted_stock = Column(Integer, nullable=True)
    status = Column(String(16), nullable=False, default="queued")
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, nullable=False, default=0)
    last_request_key = Column(String(36), nullable=True)
    last_confirmation_id = Column(Integer, nullable=True)
    reference_source = Column(String(16), nullable=True)
    error_code = Column(String(40), nullable=True)
