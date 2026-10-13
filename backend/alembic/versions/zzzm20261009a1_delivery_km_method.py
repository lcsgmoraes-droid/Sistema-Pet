"""Cria o método de registro de KM sem depender da tela de configurações.

Revision ID: zzzm20261009a1
Revises: zzzl20261009a1
"""

from alembic import op
import sqlalchemy as sa

revision = "zzzm20261009a1"
down_revision = "zzzl20261009a1"
branch_labels = None
depends_on = None


def upgrade():
    columns = sa.inspect(op.get_bind()).get_columns("configuracoes_entrega")
    # Ambientes legados podem ter recebido a coluna pelo endpoint de configuração.
    if any(column["name"] == "metodo_km_entrega" for column in columns):
        return
    op.add_column(
        "configuracoes_entrega",
        sa.Column(
            "metodo_km_entrega",
            sa.String(20),
            nullable=False,
            server_default="auto_rota",
        ),
    )


def downgrade():
    op.drop_column("configuracoes_entrega", "metodo_km_entrega")
