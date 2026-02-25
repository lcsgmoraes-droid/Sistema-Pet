"""merge_head_pos_base

Revision ID: f6c9a1b2d3e4
Revises: bda1c213cae2
Create Date: 2026-02-25 00:00:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'f6c9a1b2d3e4'
down_revision: Union[str, Sequence[str], None] = 'bda1c213cae2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
