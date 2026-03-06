"""merge_e4f5_and_g8a9

Revision ID: 31dfe937b9dd
Revises: e4f5a6b7c8d9, g8a9b0c1d2e3
Create Date: 2026-03-06 10:05:26.413433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31dfe937b9dd'
down_revision: Union[str, Sequence[str], None] = ('e4f5a6b7c8d9', 'g8a9b0c1d2e3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
