"""Configuração e entregas de XML contábil, com isolamento por empresa."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zzzzh20261019a1"
down_revision = "zzzzg20261019a1"
branch_labels = None
depends_on = None

TABLES = ("xml_contabilidade_config", "xml_contabilidade_envios")


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
        sa.Column("email_contador", sa.String(254)),
        sa.Column(
            "envio_automatico", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("envio_automatico_desde", sa.DateTime(timezone=True)),
        sa.Column(
            "envio_mensal", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("dia_envio_mensal", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "hora_envio_mensal", sa.String(5), nullable=False, server_default="08:00"
        ),
        sa.Column("proximo_envio_mensal", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", name="uq_xml_contabilidade_config_tenant"),
    )
    op.create_table(
        TABLES[1],
        *_base_columns(),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("email_destino", sa.String(254), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("agendado_para", sa.DateTime(timezone=True)),
        sa.Column("proxima_tentativa_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processamento_iniciado_em", sa.DateTime(timezone=True)),
        sa.Column("enviado_em", sa.DateTime(timezone=True)),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantidade_xml", sa.Integer()),
        sa.Column("ultimo_erro", sa.String(500)),
        sa.Column("nome_arquivo", sa.String(150)),
        sa.Column("idempotency_key", sa.String(200)),
        sa.Column("provider", sa.String(20)),
        sa.Column("documento_id", sa.String(128)),
        sa.Column("documento_status", sa.String(20)),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_xml_contabilidade_envio_dedupe"
        ),
    )
    for table in TABLES:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
    op.create_index(
        "ix_xml_contabilidade_envios_pendentes",
        TABLES[1],
        ["tenant_id", "status", "proxima_tentativa_em"],
    )
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=TABLES, enable=True)


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table)
