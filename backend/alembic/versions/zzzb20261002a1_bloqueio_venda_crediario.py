"""Bloqueio opcional de venda por atraso no crediario.

Revision ID: zzzb20261002a1
Revises: zzza20261001a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzb20261002a1"
down_revision = "zzza20261001a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa_config_geral",
        sa.Column(
            "bloquear_venda_crediario_atrasado",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "empresa_config_geral",
        sa.Column(
            "dias_atraso_bloqueio_venda",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
    )


def downgrade() -> None:
    op.drop_column("empresa_config_geral", "dias_atraso_bloqueio_venda")
    op.drop_column("empresa_config_geral", "bloquear_venda_crediario_atrasado")
