"""merge_fiscal_heads

Revision ID: c49b4a5562b5
Revises: 0c82ba32236c, fix_fiscal_tenant_id
Create Date: 2026-01-31 00:33:10.374102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c49b4a5562b5'
down_revision: Union[str, Sequence[str], None] = ('0c82ba32236c', 'fix_fiscal_tenant_id')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
