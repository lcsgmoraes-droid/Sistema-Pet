"""add missing drive columns on pedidos

Revision ID: b1c2d3e4f5a6
Revises: 9b4f1a2c7d8e
Create Date: 2026-03-09 11:48:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "9b4f1a2c7d8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.pedidos') IS NOT NULL THEN
                ALTER TABLE pedidos
                ADD COLUMN IF NOT EXISTS is_drive BOOLEAN NOT NULL DEFAULT false,
                ADD COLUMN IF NOT EXISTS drive_chegou_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS drive_entregue_at TIMESTAMPTZ;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.pedidos') IS NOT NULL THEN
                ALTER TABLE pedidos
                DROP COLUMN IF EXISTS drive_entregue_at,
                DROP COLUMN IF EXISTS drive_chegou_at,
                DROP COLUMN IF EXISTS is_drive;
            END IF;
        END $$;
        """
    )
