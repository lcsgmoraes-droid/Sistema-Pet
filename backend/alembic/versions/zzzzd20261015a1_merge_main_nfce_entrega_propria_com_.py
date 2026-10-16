"""merge main (nfce entrega propria) com documentacao

Revision ID: zzzzd20261015a1
Revises: zzzzc20261015a1, zzzo20261014a1
Create Date: 2026-10-16 02:40:49.099775

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = 'zzzzd20261015a1'
down_revision: Union[str, Sequence[str], None] = ('zzzzc20261015a1', 'zzzo20261014a1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
