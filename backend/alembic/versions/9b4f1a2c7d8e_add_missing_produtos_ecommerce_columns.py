"""add missing produtos ecommerce columns

Revision ID: 9b4f1a2c7d8e
Revises: 8a417156c290
Create Date: 2026-03-09 11:35:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b4f1a2c7d8e"
down_revision: Union[str, Sequence[str], None] = "8a417156c290"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS preco_ecommerce DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS preco_ecommerce_promo DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS preco_ecommerce_promo_inicio TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS preco_ecommerce_promo_fim TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS preco_app DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS preco_app_promo DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS preco_app_promo_inicio TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS preco_app_promo_fim TIMESTAMPTZ
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE produtos
        DROP COLUMN IF EXISTS preco_app_promo_fim,
        DROP COLUMN IF EXISTS preco_app_promo_inicio,
        DROP COLUMN IF EXISTS preco_app_promo,
        DROP COLUMN IF EXISTS preco_app,
        DROP COLUMN IF EXISTS preco_ecommerce_promo_fim,
        DROP COLUMN IF EXISTS preco_ecommerce_promo_inicio,
        DROP COLUMN IF EXISTS preco_ecommerce_promo,
        DROP COLUMN IF EXISTS preco_ecommerce
        """
    )
