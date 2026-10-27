"""historico de alteracoes do OPS nos dados das lojas

Revision ID: zzzzze20261028a1
Revises: zzzzzd20261027a1
Create Date: 2026-10-28

Registra quem alterou o que (acesso a modulos e dados da loja), quando e o valor
anterior. Tabela da plataforma, sem isolamento por loja. Idempotente: a mesma tabela
tambem existe na branch do CRM, e quem chegar primeiro ao banco a cria.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zzzzze20261028a1"
down_revision = "zzzzzd20261027a1"
branch_labels = None
depends_on = None

TABELA = "ops_tenant_change_log"


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table(TABELA):
        return
    op.create_table(
        TABELA,
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
        "ix_ops_tenant_change_log_tenant_data", TABELA, ["tenant_id", "criado_em"]
    )
    op.create_index("ix_ops_tenant_change_log_data", TABELA, ["criado_em"])


def downgrade() -> None:
    op.drop_table(TABELA)
