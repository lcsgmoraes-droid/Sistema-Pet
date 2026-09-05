"""Preferência comercial por empresa, preservando a visão atual."""

from alembic import op
import sqlalchemy as sa

revision = "zzj20260905a1"
down_revision = "zzi20260905a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "empresa_config_geral",
        sa.Column(
            "visao_comercial", sa.String(20), nullable=False, server_default="venda"
        ),
    )
    op.create_check_constraint(
        "ck_empresa_config_visao_comercial",
        "empresa_config_geral",
        "visao_comercial IN ('venda', 'recebimento')",
    )


def downgrade():
    op.drop_constraint(
        "ck_empresa_config_visao_comercial", "empresa_config_geral", type_="check"
    )
    op.drop_column("empresa_config_geral", "visao_comercial")
