"""historico de alteracoes do OPS nos dados das lojas

Revision ID: zzzzn20261023b1
Revises: zzzzm20261022a1
Create Date: 2026-10-23

Registra quem alterou o que (acesso a modulos e dados da loja), quando e o valor
anterior. Tabela da plataforma, sem isolamento por loja.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zzzzn20261023b1"
down_revision = "zzzzm20261022a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A mesma tabela tambem e criada pela migracao zzzzze (linha da main): a ordem entre
    # as duas depende do caminho, entao cada uma pula se a tabela ja existe.
    if sa.inspect(op.get_bind()).has_table("ops_tenant_change_log"):
        return
    op.create_table(
        "ops_tenant_change_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("admin_id", sa.Integer()),
        sa.Column("admin_email", sa.String(255), nullable=False),
        sa.Column("categoria", sa.String(30), nullable=False),
        sa.Column("campo", sa.String(80), nullable=False),
        sa.Column("antes", sa.Text()),
        sa.Column("depois", sa.Text()),
    )
    op.create_index(
        "ix_ops_tenant_change_log_tenant_data",
        "ops_tenant_change_log",
        ["tenant_id", "criado_em"],
    )
    op.create_index(
        "ix_ops_tenant_change_log_data", "ops_tenant_change_log", ["criado_em"]
    )


def downgrade() -> None:
    op.drop_table("ops_tenant_change_log")
