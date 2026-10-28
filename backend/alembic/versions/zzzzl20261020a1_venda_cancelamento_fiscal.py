"""Acompanha o pedido de cancelamento sem alterar a situação fiscal da nota."""

from alembic import op
import sqlalchemy as sa

revision = "zzzzl20261020a1"
down_revision = "zzzzk20261020a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "vendas", sa.Column("nfe_cancelamento_status", sa.String(20), nullable=True)
    )
    op.add_column(
        "vendas", sa.Column("nfe_cancelamento_codigo", sa.String(80), nullable=True)
    )
    op.add_column(
        "vendas", sa.Column("nfe_cancelamento_motivo", sa.String(500), nullable=True)
    )
    op.add_column(
        "vendas",
        sa.Column(
            "nfe_cancelamento_solicitado_em", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade():
    for campo in (
        "nfe_cancelamento_solicitado_em",
        "nfe_cancelamento_motivo",
        "nfe_cancelamento_codigo",
        "nfe_cancelamento_status",
    ):
        op.drop_column("vendas", campo)
