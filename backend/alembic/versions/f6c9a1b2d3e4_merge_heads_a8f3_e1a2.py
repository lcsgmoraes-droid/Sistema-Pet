"""merge_heads_a8f3_e1a2

Revision ID: f6c9a1b2d3e4
Revises: a8f3c1d2e9b4, e1a2c3d4f5b6
Create Date: 2026-02-25 00:00:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'f6c9a1b2d3e4'
down_revision: Union[str, Sequence[str], None] = ('a8f3c1d2e9b4', 'e1a2c3d4f5b6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
