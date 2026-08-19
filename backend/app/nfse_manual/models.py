from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class NfseManualDocument(BaseTenantModel):
    """Rascunho e comprovantes de uma NFS-e emitida fora do CorePet."""

    __tablename__ = "nfse_manual_documents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "reference", name="uq_nfse_manual_documents_tenant_ref"
        ),
        UniqueConstraint(
            "tenant_id",
            "invoice_number",
            name="uq_nfse_manual_documents_tenant_invoice",
        ),
        CheckConstraint(
            "status IN ('draft', 'issued', 'cancelled')",
            name="ck_nfse_manual_documents_status",
        ),
        Index(
            "ix_nfse_manual_documents_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_nfse_manual_documents_tenant_origin",
            "tenant_id",
            "origin_type",
            "origin_id",
        ),
    )

    reference = Column(String(120), nullable=False)
    status = Column(String(30), nullable=False, default="draft", index=True)
    origin_type = Column(String(50), nullable=False)
    origin_id = Column(String(80), nullable=False)
    customer_id = Column(ForeignKey("clientes.id"), nullable=True, index=True)
    consultation_id = Column(ForeignKey("vet_consultas.id"), nullable=True, index=True)
    prepared_by_user_id = Column(ForeignKey("users.id"), nullable=False)
    registered_by_user_id = Column(ForeignKey("users.id"), nullable=True)

    service_amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=False)
    service_code = Column(String(20), nullable=True)
    iss_rate = Column(Numeric(5, 2), nullable=True)
    iss_withheld = Column(Boolean, nullable=False, default=False)
    preparation_snapshot = Column(JSON, nullable=False, default=dict)

    invoice_number = Column(String(80), nullable=True, index=True)
    verification_code = Column(String(120), nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    pdf_file_name = Column(String(255), nullable=True)
    pdf_original_name = Column(String(255), nullable=True)
    pdf_sha256 = Column(String(64), nullable=True)
    xml_file_name = Column(String(255), nullable=True)
    xml_original_name = Column(String(255), nullable=True)
    xml_sha256 = Column(String(64), nullable=True)

    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
