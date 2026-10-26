"""Dados comerciais revisados antes de emitir a nota da venda."""

from alembic import op
import sqlalchemy as sa

revision = "zzzzy20261026a1"
down_revision = "zzzzx20261026a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "vendas", sa.Column("nfe_contexto_comercial", sa.JSON(), nullable=True)
    )


def downgrade():
    op.execute("SET LOCAL row_security = off")
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM vendas WHERE nfe_contexto_comercial IS NOT NULL LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError(
            "Existem dados comerciais de notas fiscais. Preserve o histórico antes de remover a coluna."
        )
    op.drop_column("vendas", "nfe_contexto_comercial")
