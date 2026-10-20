"""Acompanhamento durável de notas e eventos fiscais, isolado por empresa."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzj20261019a1"
down_revision = "zzzzi20261019a1"
branch_labels = None
depends_on = None

TABLES = (
    "xml_contabilidade_documentos_monitor",
    "xml_contabilidade_eventos_recebidos",
)


def _base_columns():
    return (
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
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
    )


def upgrade():
    op.create_table(
        TABLES[0],
        *_base_columns(),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("documento_id", sa.String(128), nullable=False),
        sa.Column("ultima_consulta_em", sa.DateTime(timezone=True)),
        sa.Column("proxima_consulta_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            "documento_id",
            name="uq_xml_contabilidade_monitor_documento",
        ),
    )
    op.create_table(
        TABLES[1],
        *_base_columns(),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("documento_id", sa.String(128), nullable=False),
        sa.Column("chave", sa.String(44), nullable=False),
        sa.Column("identidade", sa.String(54), nullable=False),
        sa.Column("tipo", sa.String(6), nullable=False),
        sa.Column("sequencia", sa.Integer(), nullable=False),
        sa.Column("protocolo", sa.String(15), nullable=False),
        sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nome_arquivo", sa.String(100), nullable=False),
        sa.Column("xml", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "identidade",
            "protocolo",
            name="uq_xml_contabilidade_evento_protocolo",
        ),
    )
    for table in TABLES:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
    op.create_index(
        "ix_xml_contabilidade_monitor_consulta",
        TABLES[0],
        ["tenant_id", "proxima_consulta_em"],
    )
    op.create_index(
        "ix_xml_contabilidade_eventos_registro",
        TABLES[1],
        ["tenant_id", "registrado_em"],
    )
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=TABLES, enable=True)


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table)
