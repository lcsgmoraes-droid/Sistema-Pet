"""merge_heads

Revision ID: 93d0f70b9342
Revises: 20260129_dre_plano_contas, 80cd0282dcd5
Create Date: 2026-01-29 01:29:38.212889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93d0f70b9342'
down_revision: Union[str, Sequence[str], None] = ('20260129_dre_plano_contas', '80cd0282dcd5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
