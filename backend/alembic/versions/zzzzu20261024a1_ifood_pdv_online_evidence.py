"""Evidencia expositiva do pagamento online no piloto DEV, sem baixa financeira.

Revision ID: zzzzu20261024a1
Revises: zzzzt20261024a1
"""

from alembic import op
import sqlalchemy as sa

revision = "zzzzu20261024a1"
down_revision = "zzzzt20261024a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ifood_pdv_bridges",
        sa.Column("online_financial_evidence", sa.JSON(), nullable=True),
    )


def downgrade():
    # Nao apagar provas de pagamentos e repasses mesmo que estejam ocultas por RLS.
    op.execute("SET LOCAL row_security = off")
    found = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM ifood_pdv_bridges WHERE online_financial_evidence IS NOT NULL LIMIT 1"
            )
        )
        .first()
    )
    if found:
        raise RuntimeError(
            "Existem evidencias de pagamento online iFood; downgrade recusado."
        )
    op.drop_column("ifood_pdv_bridges", "online_financial_evidence")
