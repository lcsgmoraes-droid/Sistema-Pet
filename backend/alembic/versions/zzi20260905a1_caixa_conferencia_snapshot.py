"""Preserva a referência usada ao conferir a abertura de caixa."""

from alembic import op
import sqlalchemy as sa

revision = "zzi20260905a1"
down_revision = "zzh20260904a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("caixas", sa.Column("conferencia_abertura", sa.JSON(), nullable=True))
    op.add_column(
        "caixas", sa.Column("fechamento_em", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("caixas", "fechamento_em")
    op.drop_column("caixas", "conferencia_abertura")
