"""Vinculo opcional do emitente IntNFe, com isolamento por empresa."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import iter_tenant_rls_statements

revision = "zzn20260909a1"
down_revision = "zzl20260909a1"
branch_labels = None
depends_on = None

TABLE = "intnfe_connections"


def upgrade():
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cnpj", sa.String(14), nullable=False),
        sa.Column("razao_social", sa.String(60), nullable=False),
        sa.Column("nome_fantasia", sa.String(60), nullable=False),
        sa.Column("integrador_id", sa.String(128), nullable=False),
        sa.Column("emitente_id", sa.String(128)),
        sa.Column("client_id", sa.String(128)),
        sa.Column("client_secret_encrypted", sa.Text()),
        sa.Column(
            "status", sa.String(40), nullable=False, server_default="nao_vinculado"
        ),
        sa.Column(
            "criacao_iniciada", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("operacao_id", sa.String(36)),
        sa.Column("operacao_iniciada_em", sa.DateTime(timezone=True)),
        sa.Column("ultimo_codigo", sa.String(64)),
        sa.Column("correlation_id", sa.String(128)),
        sa.Column("vinculado_em", sa.DateTime(timezone=True)),
        sa.Column("certificado_valido_ate", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", name="uq_intnfe_tenant"),
        sa.UniqueConstraint("cnpj", name="uq_intnfe_cnpj"),
        sa.UniqueConstraint("emitente_id", name="uq_intnfe_emitente"),
    )
    op.create_index("ix_intnfe_connections_tenant_id", TABLE, ["tenant_id"])
    if op.get_bind().dialect.name == "postgresql":
        for statement in iter_tenant_rls_statements(TABLE, enable=True):
            op.execute(statement)


def downgrade():
    op.drop_table(TABLE)
