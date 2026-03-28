"""alter vendas nfe_bling_id to bigint

Revision ID: t8u9v0w1x2y3
Revises: z9y8x7w6v5u4
Create Date: 2026-03-28 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "t8u9v0w1x2y3"
down_revision = "z9y8x7w6v5u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE vendas
        ALTER COLUMN nfe_bling_id TYPE BIGINT
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE vendas
        ALTER COLUMN nfe_bling_id TYPE INTEGER
        """
    )
