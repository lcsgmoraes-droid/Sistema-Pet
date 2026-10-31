"""Outbox por NF-e para encaminhar XMLs completos ao escritorio.

Revision ID: zzzq20261014a1
Revises: zzzp20261014a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zzzq20261014a1"
down_revision = "zzzp20261014a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sefaz_xml_encaminhamentos",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "documento_id",
            sa.Integer(),
            sa.ForeignKey("sefaz_documentos_distribuidos.id"),
            nullable=False,
        ),
        sa.Column("chave_acesso", sa.String(44), nullable=False),
        sa.Column("email_destino", sa.String(320), nullable=False),
        sa.Column("ativado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="pendente", nullable=False),
        sa.Column("tentativas", sa.Integer(), server_default="0", nullable=False),
        sa.Column("proxima_tentativa_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_erro", sa.String(255), nullable=True),
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
        sa.UniqueConstraint(
            "tenant_id", "chave_acesso", name="uq_sefaz_xml_encaminhamentos_tenant_chave"
        ),
    )
    for column in ("tenant_id", "status"):
        op.create_index(
            f"ix_sefaz_xml_encaminhamentos_{column}",
            "sefaz_xml_encaminhamentos",
            [column],
        )
    op.create_index(
        "ix_sefaz_xml_encaminhamentos_proxima_tentativa_em",
        "sefaz_xml_encaminhamentos",
        ["proxima_tentativa_em"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE sefaz_xml_encaminhamentos ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE sefaz_xml_encaminhamentos FORCE ROW LEVEL SECURITY")
        guard = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
        op.execute(
            "CREATE POLICY sefaz_xml_encaminhamentos_tenant_isolation "
            f"ON sefaz_xml_encaminhamentos USING ({guard}) WITH CHECK ({guard})"
        )


def downgrade() -> None:
    op.drop_index(
        "ix_sefaz_xml_encaminhamentos_proxima_tentativa_em",
        table_name="sefaz_xml_encaminhamentos",
    )
    for column in ("status", "tenant_id"):
        op.drop_index(
            f"ix_sefaz_xml_encaminhamentos_{column}",
            table_name="sefaz_xml_encaminhamentos",
        )
    op.drop_table("sefaz_xml_encaminhamentos")
