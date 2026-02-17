"""custos_moto_base

Revision ID: 6b592d755fb9
Revises: 268eb76af817
Create Date: 2026-02-01 10:27:23.919403

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6b592d755fb9"
down_revision = "268eb76af817"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "configuracoes_custo_moto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),

        # =========================
        # COMBUSTÍVEL
        # =========================
        sa.Column("preco_combustivel", sa.Numeric(10, 2), nullable=False),
        sa.Column("km_por_litro", sa.Numeric(10, 2), nullable=False),

        # =========================
        # MANUTENÇÕES POR KM
        # =========================
        sa.Column("km_troca_oleo", sa.Integer(), nullable=True),
        sa.Column("custo_troca_oleo", sa.Numeric(10, 2), nullable=True),

        sa.Column("km_troca_pneu_dianteiro", sa.Integer(), nullable=True),
        sa.Column("custo_pneu_dianteiro", sa.Numeric(10, 2), nullable=True),

        sa.Column("km_troca_pneu_traseiro", sa.Integer(), nullable=True),
        sa.Column("custo_pneu_traseiro", sa.Numeric(10, 2), nullable=True),

        # 🆕 KIT TRASEIRO
        sa.Column("km_troca_kit_traseiro", sa.Integer(), nullable=True),
        sa.Column("custo_kit_traseiro", sa.Numeric(10, 2), nullable=True),

        sa.Column("km_manutencao_geral", sa.Integer(), nullable=True),
        sa.Column("custo_manutencao_geral", sa.Numeric(10, 2), nullable=True),

        # =========================
        # CUSTOS FIXOS MENSAIS
        # =========================
        sa.Column("seguro_mensal", sa.Numeric(10, 2), nullable=True),

        # 🆕 LICENCIAMENTO
        sa.Column("licenciamento_mensal", sa.Numeric(10, 2), nullable=True),

        sa.Column("ipva_mensal", sa.Numeric(10, 2), nullable=True),
        sa.Column("outros_custos_mensais", sa.Numeric(10, 2), nullable=True),

        # =========================
        # CONTROLE
        # =========================
        sa.Column("km_medio_mensal", sa.Numeric(10, 2), nullable=True),

        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),

        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.UniqueConstraint("tenant_id", name="uq_config_custo_moto_tenant"),
    )


def downgrade():
    op.drop_table("configuracoes_custo_moto")
