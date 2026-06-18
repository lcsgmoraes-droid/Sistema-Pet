"""add updated_at to stone transaction logs

Revision ID: z9y8x7w6v5u4
Revises: z1a2b3c4d5e6
Create Date: 2026-03-18 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "z9y8x7w6v5u4"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE stone_transaction_logs
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE stone_transaction_logs
        DROP COLUMN IF EXISTS updated_at
        """
    )