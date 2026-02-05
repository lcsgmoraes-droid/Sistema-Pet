"""add simples nacional config to empresa_config_fiscal

Revision ID: 2e9c2acefb7b
Revises: add_company_data_001
Create Date: 2026-01-31 02:16:44.926633

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2e9c2acefb7b"
down_revision = "add_company_data_001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("simples_ativo", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("simples_anexo", sa.String(length=10), nullable=True)
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("simples_aliquota_vigente", sa.Numeric(5, 2), nullable=True)
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("simples_ultima_atualizacao", sa.Date(), nullable=True)
    )


def downgrade():
    op.drop_column("empresa_config_fiscal", "simples_ultima_atualizacao")
    op.drop_column("empresa_config_fiscal", "simples_aliquota_vigente")
    op.drop_column("empresa_config_fiscal", "simples_anexo")
    op.drop_column("empresa_config_fiscal", "simples_ativo")
