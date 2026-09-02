"""separa estoque negativo online e exibe esgotados por padrao

Revision ID: zza20260901a1
Revises: zyx20260831a1
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa


revision = "zza20260901a1"
down_revision = "zyx20260831a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tenants",
        sa.Column(
            "permite_estoque_negativo_online",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "pedidos",
        sa.Column(
            "reserva_estoque_iniciada_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    # A alteração é apenas do padrão de novos tenants. As escolhas existentes
    # permanecem intactas.
    op.alter_column(
        "tenants",
        "ecommerce_ocultar_sem_estoque",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )


def downgrade():
    op.drop_column("pedidos", "reserva_estoque_iniciada_at")
    op.alter_column(
        "tenants",
        "ecommerce_ocultar_sem_estoque",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )
    op.drop_column("tenants", "permite_estoque_negativo_online")
