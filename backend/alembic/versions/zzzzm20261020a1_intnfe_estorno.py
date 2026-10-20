"""Estorno fiscal separado, tentativa durável e projeção de regularização na venda."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzm20261020a1"
down_revision = "zzzzl20261020a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "intnfe_estornos",
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
        sa.Column(
            "venda_id",
            sa.Integer(),
            sa.ForeignKey("vendas.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("ambiente_codigo", sa.SmallInteger(), nullable=False),
        sa.Column("original_chave", sa.String(44), nullable=False),
        sa.Column("original_xml_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("motivo_operacao", sa.String(500), nullable=False),
        sa.Column("declarado_nao_realizada", sa.Boolean(), nullable=False),
        sa.Column("solicitado_por", sa.Integer(), nullable=True),
        sa.Column("tentativa_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=True),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("serie", sa.Integer(), nullable=True),
        sa.Column("chave", sa.String(44), nullable=True),
        sa.Column("protocolo", sa.String(50), nullable=True),
        sa.Column("codigo", sa.String(80), nullable=True),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.Column("xml", sa.Text(), nullable=True),
        sa.Column(
            "xml_validado", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("autorizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "tenant_id",
            "venda_id",
            "ambiente_codigo",
            name="uq_intnfe_estorno_venda_ambiente",
        ),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_intnfe_estorno_idempotency"
        ),
    )
    op.create_index("ix_intnfe_estornos_tenant_id", "intnfe_estornos", ["tenant_id"])
    apply_tenant_rls(
        op_module=op, sa_module=sa, table_names=("intnfe_estornos",), enable=True
    )
    for name, tipo in (
        ("nfe_estorno_status", sa.String(20)),
        ("nfe_estorno_numero", sa.Integer()),
        ("nfe_estorno_serie", sa.Integer()),
        ("nfe_estorno_protocolo", sa.String(50)),
    ):
        op.add_column("vendas", sa.Column(name, tipo, nullable=True))


def downgrade():
    for name in (
        "nfe_estorno_protocolo",
        "nfe_estorno_serie",
        "nfe_estorno_numero",
        "nfe_estorno_status",
    ):
        op.drop_column("vendas", name)
    op.drop_table("intnfe_estornos")
