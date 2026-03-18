"""merge heads 9d4b and z9y8

Revision ID: c7d8e9f0a1b2
Revises: 9d4b8c2a1f0e, z9y8x7w6v5u4
Create Date: 2026-03-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = ('9d4b8c2a1f0e', 'z9y8x7w6v5u4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass