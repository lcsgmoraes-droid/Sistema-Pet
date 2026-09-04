"""adiciona margens sugeridas para formar preco de venda

Revision ID: zzc20260903a1
Revises: zzb20260903a1
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa

revision = "zzc20260903a1"
down_revision = "zzb20260903a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Apenas cria as preferências da empresa. Nenhum preço de produto é recalculado.
    op.add_column(
        "empresa_config_geral",
        sa.Column(
            "margem_preco_sugestao_1",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("30.00"),
        ),
    )
    op.add_column(
        "empresa_config_geral",
        sa.Column(
            "margem_preco_sugestao_2",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("34.00"),
        ),
    )


def downgrade() -> None:
    op.drop_column("empresa_config_geral", "margem_preco_sugestao_2")
    op.drop_column("empresa_config_geral", "margem_preco_sugestao_1")
