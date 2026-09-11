"""NFS-e manual assistida e parametros fiscais

Revision ID: ifs20260819a1
Revises: ifr20260816a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "ifs20260819a1"
down_revision = "ifr20260816a1"
branch_labels = None
depends_on = None

TABLES = ("nfse_manual_documents",)


def upgrade() -> None:
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("municipio_iss_codigo", sa.String(length=7), nullable=True),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("nfse_item_lista_servico", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column(
            "nfse_natureza_operacao",
            sa.String(length=1),
            server_default="1",
            nullable=True,
        ),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("nfse_portal_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("nfse_regime_especial_tributacao", sa.String(length=1)),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column(
            "nfse_incentivador_cultural",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=True,
        ),
    )

    op.create_table(
        "nfse_manual_documents",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=False),
        sa.Column(
            "status", sa.String(length=30), server_default="draft", nullable=False
        ),
        sa.Column("origin_type", sa.String(length=50), nullable=False),
        sa.Column("origin_id", sa.String(length=80), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("consultation_id", sa.Integer(), nullable=True),
        sa.Column("prepared_by_user_id", sa.Integer(), nullable=False),
        sa.Column("registered_by_user_id", sa.Integer(), nullable=True),
        sa.Column("service_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("service_code", sa.String(length=20), nullable=True),
        sa.Column("iss_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "iss_withheld", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("preparation_snapshot", sa.JSON(), nullable=False),
        sa.Column("invoice_number", sa.String(length=80), nullable=True),
        sa.Column("verification_code", sa.String(length=120), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("pdf_file_name", sa.String(length=255), nullable=True),
        sa.Column("pdf_original_name", sa.String(length=255), nullable=True),
        sa.Column("pdf_sha256", sa.String(length=64), nullable=True),
        sa.Column("xml_file_name", sa.String(length=255), nullable=True),
        sa.Column("xml_original_name", sa.String(length=255), nullable=True),
        sa.Column("xml_sha256", sa.String(length=64), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["customer_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["consultation_id"], ["vet_consultas.id"]),
        sa.ForeignKeyConstraint(["prepared_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["registered_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('draft', 'issued', 'cancelled')",
            name="ck_nfse_manual_documents_status",
        ),
        sa.UniqueConstraint(
            "tenant_id", "reference", name="uq_nfse_manual_documents_tenant_ref"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "invoice_number",
            name="uq_nfse_manual_documents_tenant_invoice",
        ),
    )
    op.create_index(
        "ix_nfse_manual_documents_tenant_id", "nfse_manual_documents", ["tenant_id"]
    )
    op.create_index(
        "ix_nfse_manual_documents_status", "nfse_manual_documents", ["status"]
    )
    op.create_index(
        "ix_nfse_manual_documents_customer_id", "nfse_manual_documents", ["customer_id"]
    )
    op.create_index(
        "ix_nfse_manual_documents_consultation_id",
        "nfse_manual_documents",
        ["consultation_id"],
    )
    op.create_index(
        "ix_nfse_manual_documents_invoice_number",
        "nfse_manual_documents",
        ["invoice_number"],
    )
    op.create_index(
        "ix_nfse_manual_documents_tenant_origin",
        "nfse_manual_documents",
        ["tenant_id", "origin_type", "origin_id"],
    )
    op.create_index(
        "ix_nfse_manual_documents_tenant_status",
        "nfse_manual_documents",
        ["tenant_id", "status"],
    )
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=TABLES, enable=True)


def downgrade() -> None:
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=TABLES, enable=False)
    op.drop_table("nfse_manual_documents")
    op.drop_column("empresa_config_fiscal", "nfse_portal_url")
    op.drop_column("empresa_config_fiscal", "nfse_incentivador_cultural")
    op.drop_column("empresa_config_fiscal", "nfse_regime_especial_tributacao")
    op.drop_column("empresa_config_fiscal", "nfse_natureza_operacao")
    op.drop_column("empresa_config_fiscal", "nfse_item_lista_servico")
    op.drop_column("empresa_config_fiscal", "municipio_iss_codigo")
