"""fix_empresa_config_fiscal_use_base_tenant_model

Revision ID: 18d477dfc884
Revises: c49b4a5562b5
Create Date: 2026-01-31 01:04:59.707537

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18d477dfc884'
down_revision: Union[str, Sequence[str], None] = 'c49b4a5562b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
