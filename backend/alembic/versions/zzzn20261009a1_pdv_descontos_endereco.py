"""Separa desconto manual da venda e configura endereço na busca do PDV.

Revision ID: zzzn20261009a1
Revises: zzzm20261009a1
"""

from alembic import op
import sqlalchemy as sa

revision = "zzzn20261009a1"
down_revision = "zzzm20261009a1"
branch_labels = None
depends_on = None


def upgrade():
    # NULL identifica vendas legadas sem origem separada dos descontos.
    op.add_column(
        "vendas",
        sa.Column("desconto_venda_valor", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "empresa_config_geral",
        sa.Column(
            "mostrar_endereco_cliente_pdv",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade():
    op.drop_column("empresa_config_geral", "mostrar_endereco_cliente_pdv")
    op.drop_column("vendas", "desconto_venda_valor")
