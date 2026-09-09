"""Origem do cliente; historico sem evidencia permanece nao identificado."""

from alembic import op
import sqlalchemy as sa

revision = "zzl20260909a1"
down_revision = "zzk20260907a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clientes", sa.Column("origem_cliente", sa.String(50), nullable=True))
    op.create_index(
        "ix_clientes_tenant_origem_cadastro",
        "clientes",
        ["tenant_id", "origem_cliente", "created_at"],
    )


def downgrade():
    op.drop_index("ix_clientes_tenant_origem_cadastro", table_name="clientes")
    op.drop_column("clientes", "origem_cliente")
