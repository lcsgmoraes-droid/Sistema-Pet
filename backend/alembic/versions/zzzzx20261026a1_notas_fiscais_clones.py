"""Rascunhos de clonagem fiscal isolados da venda e de efeitos comerciais."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzx20261026a1"
down_revision = "zzzzw20261025a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notas_fiscais_clones",
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
        sa.Column("origem", sa.JSON(), nullable=False),
        sa.Column("dados", sa.JSON(), nullable=False),
        sa.Column("xml_origem", sa.Text(), nullable=False),
        sa.Column("modelo", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("enviado_em", sa.DateTime(timezone=True)),
        sa.Column("correlation_id", sa.String(128)),
        sa.Column("numero", sa.String(20)),
        sa.Column("chave", sa.String(44)),
        sa.Column("protocolo", sa.String(128)),
        sa.Column("motivo", sa.Text()),
        sa.Column("xml", sa.Text()),
        sa.Column("cancelamento_status", sa.String(20)),
        sa.Column("cancelamento_codigo", sa.String(80)),
        sa.Column("cancelamento_motivo", sa.Text()),
        sa.Column("cancelamento_solicitado_em", sa.DateTime(timezone=True)),
        sa.CheckConstraint("modelo IN (55,65)", name="ck_nf_clone_modelo"),
    )
    op.create_index(
        "ix_notas_fiscais_clones_tenant_id", "notas_fiscais_clones", ["tenant_id"]
    )
    apply_tenant_rls(
        op_module=op, sa_module=sa, table_names=("notas_fiscais_clones",), enable=True
    )


def downgrade():
    bind = op.get_bind()
    op.execute("SET LOCAL row_security = off")
    if bind.execute(sa.text("SELECT 1 FROM notas_fiscais_clones LIMIT 1")).first():
        raise RuntimeError(
            "Existem rascunhos ou documentos fiscais clonados; preserve o histórico."
        )
    op.drop_table("notas_fiscais_clones")
