"""adiciona textos configuraveis ao recibo do pdv

Revision ID: zzb20260903a1
Revises: zza20260901a1
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa

revision = "zzb20260903a1"
down_revision = "zza20260901a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("cupom_cabecalho", sa.Text(), nullable=True))
    op.add_column(
        "tenants", sa.Column("cupom_mensagem_final", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("tenants", "cupom_mensagem_final")
    op.drop_column("tenants", "cupom_cabecalho")
