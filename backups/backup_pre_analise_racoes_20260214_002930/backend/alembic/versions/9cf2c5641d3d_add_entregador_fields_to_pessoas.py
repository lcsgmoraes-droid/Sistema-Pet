"""add entregador fields to pessoas

Revision ID: 9cf2c5641d3d
Revises: b6c3d953f02a
Create Date: 2026-01-31 16:13:37.404341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cf2c5641d3d'
down_revision: Union[str, Sequence[str], None] = 'b6c3d953f02a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
