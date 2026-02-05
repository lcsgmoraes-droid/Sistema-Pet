"""merge_dre_integration

Revision ID: eb865c9b7f94
Revises: 20260129_dre_lancamentos, 93d0f70b9342
Create Date: 2026-01-29 09:07:23.934990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb865c9b7f94'
down_revision: Union[str, Sequence[str], None] = ('20260129_dre_lancamentos', '93d0f70b9342')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
