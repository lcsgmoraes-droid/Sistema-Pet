"""convert_vendas_id_to_identity_always

Revision ID: 35ed26f476f0
Revises: a4f3912c6f3f
Create Date: 2026-01-26 14:56:30.182762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35ed26f476f0'
down_revision: Union[str, Sequence[str], None] = 'a4f3912c6f3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
