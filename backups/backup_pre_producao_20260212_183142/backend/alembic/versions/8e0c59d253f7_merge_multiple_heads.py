"""merge multiple heads

Revision ID: 8e0c59d253f7
Revises: add_auditoria_dre_001, 5ef6def33250
Create Date: 2026-01-31 13:36:18.623239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e0c59d253f7'
down_revision: Union[str, Sequence[str], None] = ('add_auditoria_dre_001', '5ef6def33250')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
