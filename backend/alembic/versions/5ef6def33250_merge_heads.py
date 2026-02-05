"""merge heads

Revision ID: 5ef6def33250
Revises: 20260131_controle_processamento, 509ef54ba7af
Create Date: 2026-01-31 03:27:20.580337

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ef6def33250'
down_revision: Union[str, Sequence[str], None] = ('20260131_controle_processamento', '509ef54ba7af')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
