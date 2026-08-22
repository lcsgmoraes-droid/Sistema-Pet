"""add fixed delivery prices by distance tier

Revision ID: zwt20260821a1
Revises: zwq20260821a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "zwt20260821a1"
down_revision = "zwq20260821a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "configuracoes_entrega",
        sa.Column(
            "faixas_distancia",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column("valor_km_excedente", sa.Numeric(10, 2), nullable=True),
    )


def downgrade():
    op.drop_column("configuracoes_entrega", "valor_km_excedente")
    op.drop_column("configuracoes_entrega", "faixas_distancia")
