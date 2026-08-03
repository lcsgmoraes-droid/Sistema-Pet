"""centraliza parametros fiscais da NFS-e na configuracao da empresa

Revision ID: zwt20260803a1
Revises: zws20260803a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zwt20260803a1"
down_revision = "zws20260803a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("municipio_iss_codigo", sa.String(length=7), nullable=True),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("nfse_item_lista_servico", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column(
            "nfse_natureza_operacao",
            sa.String(length=1),
            server_default="1",
            nullable=True,
        ),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column(
            "nfse_regime_especial_tributacao", sa.String(length=1), nullable=True
        ),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column(
            "nfse_incentivador_cultural",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("empresa_config_fiscal", "nfse_incentivador_cultural")
    op.drop_column("empresa_config_fiscal", "nfse_regime_especial_tributacao")
    op.drop_column("empresa_config_fiscal", "nfse_natureza_operacao")
    op.drop_column("empresa_config_fiscal", "nfse_item_lista_servico")
    op.drop_column("empresa_config_fiscal", "municipio_iss_codigo")
