"""merge heads drive fields

Revision ID: 8a417156c290
Revises: 60a7b78b30b8, k4l5m6n7o8p9
Create Date: 2026-03-09 10:49:14.276902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a417156c290'
down_revision: Union[str, Sequence[str], None] = ('60a7b78b30b8', 'k4l5m6n7o8p9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
