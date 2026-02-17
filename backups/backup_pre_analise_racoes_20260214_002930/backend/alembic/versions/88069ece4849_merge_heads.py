"""Merge heads

Revision ID: 88069ece4849
Revises: 20260201_rotas_paradas, fix_conf_entrega_001
Create Date: 2026-02-01 23:42:09.854870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88069ece4849'
down_revision: Union[str, Sequence[str], None] = ('20260201_rotas_paradas', 'fix_conf_entrega_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
