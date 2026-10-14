"""Autorizacao individual para liberar venda com crediario em atraso.

Revision ID: zzzd20261003a1
Revises: zzzc20261002a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzd20261003a1"
down_revision = "zzzc20261002a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_tenants",
        sa.Column(
            "pode_liberar_venda_crediario_atrasado",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_tenants", "pode_liberar_venda_crediario_atrasado")
