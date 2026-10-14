"""Preferência de emissão automática de nota no PDV por empresa."""

from alembic import op
import sqlalchemy as sa

revision = "zzzo20261014a1"
down_revision = "zzzn20261009a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa_config_geral",
        sa.Column(
            "emitir_nota_automatica_pdv",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "empresa_config_geral",
        sa.Column(
            "tipo_nota_automatica_pdv",
            sa.String(length=4),
            nullable=False,
            server_default="nfce",
        ),
    )


def downgrade() -> None:
    op.drop_column("empresa_config_geral", "tipo_nota_automatica_pdv")
    op.drop_column("empresa_config_geral", "emitir_nota_automatica_pdv")
