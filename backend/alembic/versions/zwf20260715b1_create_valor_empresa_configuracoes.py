"""create valor empresa configuracoes

Revision ID: zwf20260715b1
Revises: zwf20260715a1
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zwf20260715b1"
down_revision = "zwf20260715a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "valor_empresa_configuracoes",
        sa.Column("periodo_dias", sa.Integer(), nullable=False),
        sa.Column("canais", sa.String(length=300), nullable=False),
        sa.Column("fornecedor_ids_excluidos", sa.JSON(), nullable=False),
        sa.Column("folha_mensal_override", sa.Numeric(14, 2), nullable=True),
        sa.Column("despesas_fixas_mensais_override", sa.Numeric(14, 2), nullable=True),
        sa.Column("margem_contribuicao_override", sa.Numeric(7, 4), nullable=True),
        sa.Column("imobilizado_override", sa.Numeric(14, 2), nullable=True),
        sa.Column("outros_ativos", sa.Numeric(14, 2), nullable=False),
        sa.Column("incluir_dividas", sa.Boolean(), nullable=False),
        sa.Column("percentual_dividas_assumidas", sa.Numeric(7, 4), nullable=False),
        sa.Column("desconto_estoque_conservador", sa.Numeric(7, 4), nullable=False),
        sa.Column("desconto_estoque_provavel", sa.Numeric(7, 4), nullable=False),
        sa.Column("desconto_estoque_otimista", sa.Numeric(7, 4), nullable=False),
        sa.Column("multiplo_lucro_conservador", sa.Numeric(7, 4), nullable=False),
        sa.Column("multiplo_lucro_provavel", sa.Numeric(7, 4), nullable=False),
        sa.Column("multiplo_lucro_otimista", sa.Numeric(7, 4), nullable=False),
        sa.Column("dias_estoque_lento", sa.Integer(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_valor_empresa_configuracoes_tenant"),
    )
    op.create_index(
        op.f("ix_valor_empresa_configuracoes_tenant_id"),
        "valor_empresa_configuracoes",
        ["tenant_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_valor_empresa_configuracoes_tenant_id"), table_name="valor_empresa_configuracoes")
    op.drop_table("valor_empresa_configuracoes")
