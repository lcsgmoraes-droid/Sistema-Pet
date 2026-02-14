"""add_duplicatas_ignoradas_table

Revision ID: 0d8fd366fe11
Revises: 86967908c0e9
Create Date: 2026-02-14 19:02:47.189253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d8fd366fe11'
down_revision: Union[str, Sequence[str], None] = '86967908c0e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
