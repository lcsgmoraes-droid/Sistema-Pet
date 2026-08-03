"""nfse focus pilot foundation

Revision ID: zws20260803a1
Revises: zwr20260801a1
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zws20260803a1"
down_revision = "zwr20260801a1"
branch_labels = None
depends_on = None

TABLES = ("nfse_tenant_configs", "nfse_documents")


def upgrade() -> None:
    op.create_table(
        "nfse_tenant_configs",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=40),
            server_default="pending_configuration",
            nullable=False,
        ),
        sa.Column(
            "provider", sa.String(length=40), server_default="focus_nfe", nullable=False
        ),
        sa.Column(
            "environment",
            sa.String(length=20),
            server_default="homologacao",
            nullable=False,
        ),
        sa.Column("provider_company_reference", sa.String(length=120), nullable=True),
        sa.Column("focus_master_token_encrypted", sa.Text(), nullable=True),
        sa.Column("focus_homologation_token_encrypted", sa.Text(), nullable=True),
        sa.Column("focus_production_token_encrypted", sa.Text(), nullable=True),
        sa.Column("municipal_login_encrypted", sa.Text(), nullable=True),
        sa.Column("municipal_password_encrypted", sa.Text(), nullable=True),
        sa.Column("onboarding_method", sa.String(length=30), nullable=True),
        sa.Column("certificate_shared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certificate_shared_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "provider_onboarding_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("last_validation_error", sa.Text(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["certificate_shared_by_user_id"],
            ["users.id"],
        ),
        sa.UniqueConstraint("tenant_id", name="uq_nfse_tenant_configs_tenant"),
    )
    op.create_index(
        "ix_nfse_tenant_configs_tenant_id",
        "nfse_tenant_configs",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_nfse_tenant_configs_status",
        "nfse_tenant_configs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "nfse_documents",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "provider", sa.String(length=40), server_default="focus_nfe", nullable=False
        ),
        sa.Column("environment", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=50), server_default="sending", nullable=False
        ),
        sa.Column("origin_type", sa.String(length=50), nullable=False),
        sa.Column("origin_id", sa.String(length=80), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("consultation_id", sa.Integer(), nullable=True),
        sa.Column("issued_by_user_id", sa.Integer(), nullable=False),
        sa.Column("service_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("provider_status", sa.String(length=80), nullable=True),
        sa.Column("invoice_number", sa.String(length=80), nullable=True),
        sa.Column("verification_code", sa.String(length=120), nullable=True),
        sa.Column("access_key", sa.String(length=80), nullable=True),
        sa.Column("pdf_url", sa.String(length=1000), nullable=True),
        sa.Column("xml_url", sa.String(length=1000), nullable=True),
        sa.Column("provider_response", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["consultation_id"], ["vet_consultas.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "reference", name="uq_nfse_documents_tenant_reference"
        ),
    )
    op.create_index("ix_nfse_documents_tenant_id", "nfse_documents", ["tenant_id"])
    op.create_index("ix_nfse_documents_status", "nfse_documents", ["status"])
    op.create_index("ix_nfse_documents_customer_id", "nfse_documents", ["customer_id"])
    op.create_index(
        "ix_nfse_documents_consultation_id", "nfse_documents", ["consultation_id"]
    )
    op.create_index(
        "ix_nfse_documents_invoice_number", "nfse_documents", ["invoice_number"]
    )
    op.create_index("ix_nfse_documents_access_key", "nfse_documents", ["access_key"])
    op.create_index(
        "ix_nfse_documents_tenant_origin",
        "nfse_documents",
        ["tenant_id", "origin_type", "origin_id"],
    )

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABLES,
        enable=False,
    )
    op.drop_table("nfse_documents")
    op.drop_table("nfse_tenant_configs")
