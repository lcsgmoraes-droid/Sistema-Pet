from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class NfseTenantConfig(BaseTenantModel):
    """Configuracao do emissor de servico, sempre isolada por tenant."""

    __tablename__ = "nfse_tenant_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_nfse_tenant_configs_tenant"),
    )

    status = Column(
        String(40), nullable=False, default="pending_configuration", index=True
    )
    provider = Column(String(40), nullable=False, default="focus_nfe")
    environment = Column(String(20), nullable=False, default="homologacao")
    provider_company_reference = Column(String(120), nullable=True)
    focus_master_token_encrypted = Column(Text, nullable=True)
    focus_homologation_token_encrypted = Column(Text, nullable=True)
    focus_production_token_encrypted = Column(Text, nullable=True)
    municipal_login_encrypted = Column(Text, nullable=True)
    municipal_password_encrypted = Column(Text, nullable=True)
    onboarding_method = Column(String(30), nullable=True)
    certificate_shared_at = Column(DateTime(timezone=True), nullable=True)
    certificate_shared_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    provider_onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)
    last_validation_error = Column(Text, nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)


class NfseDocument(BaseTenantModel):
    """Espelho operacional de uma NFS-e emitida por um provedor parceiro."""

    __tablename__ = "nfse_documents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "reference", name="uq_nfse_documents_tenant_reference"
        ),
        Index(
            "ix_nfse_documents_tenant_origin",
            "tenant_id",
            "origin_type",
            "origin_id",
        ),
    )

    reference = Column(String(120), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    provider = Column(String(40), nullable=False, default="focus_nfe")
    environment = Column(String(20), nullable=False)
    status = Column(String(50), nullable=False, default="sending", index=True)
    origin_type = Column(String(50), nullable=False)
    origin_id = Column(String(80), nullable=False)
    customer_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    consultation_id = Column(
        Integer, ForeignKey("vet_consultas.id"), nullable=True, index=True
    )
    issued_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=False)
    provider_status = Column(String(80), nullable=True)
    invoice_number = Column(String(80), nullable=True, index=True)
    verification_code = Column(String(120), nullable=True)
    access_key = Column(String(80), nullable=True, index=True)
    pdf_url = Column(String(1000), nullable=True)
    xml_url = Column(String(1000), nullable=True)
    provider_response = Column(JSON, nullable=True)
    error_code = Column(String(80), nullable=True)
    error_message = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    authorized_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
