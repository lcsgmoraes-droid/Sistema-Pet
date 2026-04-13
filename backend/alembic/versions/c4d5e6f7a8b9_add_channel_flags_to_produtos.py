"""add channel flags to produtos

Revision ID: c4d5e6f7a8b9
Revises: u9v8w7x6y5z4
Create Date: 2026-04-12 21:45:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "u9v8w7x6y5z4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS anunciar_ecommerce BOOLEAN NOT NULL DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS anunciar_app BOOLEAN NOT NULL DEFAULT TRUE
        """
    )

    op.execute(
        """
        UPDATE produtos
        SET
            anunciar_ecommerce = FALSE,
            anunciar_app = FALSE
        WHERE COALESCE(ativo, TRUE) = FALSE
           OR COALESCE(situacao, TRUE) = FALSE
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE produtos
        DROP COLUMN IF EXISTS anunciar_app,
        DROP COLUMN IF EXISTS anunciar_ecommerce
        """
    )
