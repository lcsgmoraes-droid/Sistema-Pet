"""merge_heads

Revision ID: 7b41c090e7bf
Revises: expand_version, fix_users_tenant
Create Date: 2026-01-27 14:29:13.761755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b41c090e7bf'
down_revision: Union[str, Sequence[str], None] = ('expand_version', 'fix_users_tenant')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
