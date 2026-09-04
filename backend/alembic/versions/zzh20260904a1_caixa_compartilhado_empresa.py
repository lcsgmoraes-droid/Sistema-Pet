"""adiciona modo de caixa compartilhado por empresa

Revision ID: zzh20260904a1
Revises: zzg20260904a1
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa


revision = "zzh20260904a1"
down_revision = "zzg20260904a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa_config_geral",
        sa.Column(
            "caixa_compartilhado",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("caixas", sa.Column("usuario_fechamento_id", sa.Integer()))
    op.add_column(
        "caixas", sa.Column("usuario_fechamento_nome", sa.String(length=200))
    )


def downgrade() -> None:
    op.drop_column("caixas", "usuario_fechamento_nome")
    op.drop_column("caixas", "usuario_fechamento_id")
    op.drop_column("empresa_config_geral", "caixa_compartilhado")
