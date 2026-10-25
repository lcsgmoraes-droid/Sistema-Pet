"""Separa observacao humana de referencia operacional do estoque iFood.

Revision ID: zzzzx20261025a1
Revises: zzzzw20261025a1
"""

from alembic import op
import sqlalchemy as sa

revision = "zzzzx20261025a1"
down_revision = "zzzzw20261025a1"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "ck_ifood_catalog_confirmation_kind",
        "ifood_catalog_confirmations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_ifood_catalog_confirmation_kind",
        "ifood_catalog_confirmations",
        "kind IN ('link','portal','observation')",
    )


def downgrade():
    op.execute("SET LOCAL row_security = off")
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM ifood_catalog_confirmations WHERE kind = 'observation' LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError(
            "Existe observacao humana iFood; downgrade recusado para preservar historico."
        )
    op.drop_constraint(
        "ck_ifood_catalog_confirmation_kind",
        "ifood_catalog_confirmations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_ifood_catalog_confirmation_kind",
        "ifood_catalog_confirmations",
        "kind IN ('link','portal')",
    )
