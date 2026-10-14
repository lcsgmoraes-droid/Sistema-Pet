"""Permite exigir indicação de vendedor no PDV por empresa.

Revision ID: zzzi20261006a1
Revises: zzzh20261006a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzi20261006a1"
down_revision = "zzzh20261006a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa_config_geral",
        sa.Column("vendedor_obrigatorio_pdv", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("empresa_config_geral", "vendedor_obrigatorio_pdv")
