"""Destino e dados do pagamento nas baixas de contas a receber."""

from alembic import op
import sqlalchemy as sa

revision = "zzzzz20261026a2"
down_revision = "zzzzz20261026a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recebimentos", sa.Column("caixa_id", sa.Integer(), nullable=True))
    op.add_column(
        "recebimentos", sa.Column("conta_bancaria_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "recebimentos",
        sa.Column("numero_parcelas", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "recebimentos", sa.Column("operadora_id", sa.Integer(), nullable=True)
    )
    op.add_column("recebimentos", sa.Column("bandeira", sa.String(30), nullable=True))
    op.add_column(
        "recebimentos", sa.Column("nsu_cartao", sa.String(100), nullable=True)
    )
    op.create_foreign_key(
        "fk_recebimentos_caixa", "recebimentos", "caixas", ["caixa_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_recebimentos_conta_bancaria",
        "recebimentos",
        "contas_bancarias",
        ["conta_bancaria_id"],
        ["id"],
    )
    op.create_index("ix_recebimentos_caixa_id", "recebimentos", ["caixa_id"])


def downgrade():
    op.execute("SET LOCAL row_security = off")
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM recebimentos WHERE caixa_id IS NOT NULL OR conta_bancaria_id IS NOT NULL OR operadora_id IS NOT NULL OR numero_parcelas > 1 OR nsu_cartao IS NOT NULL OR bandeira IS NOT NULL LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError(
            "Existem recebimentos com dados financeiros. Preserve o histórico antes de remover as colunas."
        )
    op.drop_index("ix_recebimentos_caixa_id", "recebimentos")
    op.drop_constraint("fk_recebimentos_caixa", "recebimentos", type_="foreignkey")
    op.drop_constraint(
        "fk_recebimentos_conta_bancaria", "recebimentos", type_="foreignkey"
    )
    for column in (
        "nsu_cartao",
        "bandeira",
        "operadora_id",
        "numero_parcelas",
        "conta_bancaria_id",
        "caixa_id",
    ):
        op.drop_column("recebimentos", column)
