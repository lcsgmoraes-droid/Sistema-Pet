"""Registra eventos estruturados de devolucao para a DRE.

Revision ID: dredev20261005a1
Revises: zzzd20261003a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "dredev20261005a1"
down_revision = "zzzd20261003a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendas_devolucoes",
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
        sa.Column("chave_operacao", sa.String(length=36), nullable=False),
        sa.Column("requisicao_hash", sa.String(length=64), nullable=False),
        sa.Column("resposta", sa.JSON(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("data_competencia", sa.Date(), nullable=False),
        sa.Column("canal", sa.String(length=50), nullable=False),
        sa.Column("status_original_venda", sa.String(length=30), nullable=False),
        sa.Column("forma_estorno", sa.String(length=20), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("valor_devolvido", sa.Numeric(12, 2), nullable=False),
        sa.Column("custo_produtos_estornado", sa.Numeric(12, 2), nullable=False),
        sa.Column("custo_servicos_estornado", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "custo_pendente", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("itens", sa.JSON(), nullable=False),
        sa.Column(
            "movimentacao_caixa_id",
            sa.Integer(),
            sa.ForeignKey("movimentacoes_caixa.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_vendas_devolucoes_tenant_data_canal",
        "vendas_devolucoes",
        ["tenant_id", "data_competencia", "canal"],
    )
    op.create_index(
        "ix_vendas_devolucoes_tenant_venda",
        "vendas_devolucoes",
        ["tenant_id", "venda_id"],
    )
    op.create_index(
        "uq_vendas_devolucoes_tenant_chave",
        "vendas_devolucoes",
        ["tenant_id", "chave_operacao"],
        unique=True,
    )
    op.create_index(
        "ix_vendas_devolucoes_tenant_id", "vendas_devolucoes", ["tenant_id"]
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE vendas_devolucoes ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE vendas_devolucoes FORCE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY vendas_devolucoes_tenant_isolation ON vendas_devolucoes "
            "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP POLICY IF EXISTS vendas_devolucoes_tenant_isolation ON vendas_devolucoes"
        )
        op.execute("ALTER TABLE vendas_devolucoes NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE vendas_devolucoes DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_vendas_devolucoes_tenant_id", table_name="vendas_devolucoes")
    op.drop_index("uq_vendas_devolucoes_tenant_chave", table_name="vendas_devolucoes")
    op.drop_index("ix_vendas_devolucoes_tenant_venda", table_name="vendas_devolucoes")
    op.drop_index(
        "ix_vendas_devolucoes_tenant_data_canal", table_name="vendas_devolucoes"
    )
    op.drop_table("vendas_devolucoes")
