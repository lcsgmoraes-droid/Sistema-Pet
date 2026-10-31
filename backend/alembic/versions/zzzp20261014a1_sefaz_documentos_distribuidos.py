"""Guarda duravel dos documentos distribuidos pela SEFAZ.

Revision ID: zzzp20261014a1
Revises: zzzo20261014a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zzzp20261014a1"
down_revision = "zzzo20261014a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sefaz_documentos_distribuidos",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nsu", sa.String(15), nullable=False),
        sa.Column("schema", sa.String(100), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("raw_xml", sa.Text(), nullable=False),
        sa.Column("chave_acesso", sa.String(44), nullable=True),
        sa.Column("emitente_cnpj", sa.String(14), nullable=True),
        sa.Column("emitente_nome", sa.String(255), nullable=True),
        sa.Column("numero_nota", sa.String(20), nullable=True),
        sa.Column("data_emissao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valor_total", sa.Numeric(15, 2), nullable=True),
        sa.Column(
            "status", sa.String(30), server_default="outro_documento", nullable=False
        ),
        sa.Column(
            "nota_entrada_id",
            sa.Integer(),
            sa.ForeignKey("notas_entrada.id"),
            nullable=True,
        ),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.Column("processado_em", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("tenant_id", "nsu", name="uq_sefaz_documentos_tenant_nsu"),
    )
    op.create_index(
        "ix_sefaz_documentos_distribuidos_tenant_id",
        "sefaz_documentos_distribuidos",
        ["tenant_id"],
    )
    op.create_index(
        "ix_sefaz_documentos_distribuidos_chave_acesso",
        "sefaz_documentos_distribuidos",
        ["chave_acesso"],
    )
    op.create_index(
        "ix_sefaz_documentos_distribuidos_status",
        "sefaz_documentos_distribuidos",
        ["status"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE sefaz_documentos_distribuidos ENABLE ROW LEVEL SECURITY"
        )
        op.execute("ALTER TABLE sefaz_documentos_distribuidos FORCE ROW LEVEL SECURITY")
        guard = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
        op.execute(
            "CREATE POLICY sefaz_documentos_distribuidos_tenant_isolation "
            f"ON sefaz_documentos_distribuidos USING ({guard}) WITH CHECK ({guard})"
        )


def downgrade() -> None:
    op.drop_index(
        "ix_sefaz_documentos_distribuidos_status",
        table_name="sefaz_documentos_distribuidos",
    )
    op.drop_index(
        "ix_sefaz_documentos_distribuidos_chave_acesso",
        table_name="sefaz_documentos_distribuidos",
    )
    op.drop_index(
        "ix_sefaz_documentos_distribuidos_tenant_id",
        table_name="sefaz_documentos_distribuidos",
    )
    op.drop_table("sefaz_documentos_distribuidos")
