"""merge_heads

Revision ID: 48dad2e87a0d
Revises: 20260207_add_observacoes, sprint8_security_lgpd
Create Date: 2026-02-08 23:26:57.762151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48dad2e87a0d'
down_revision: Union[str, Sequence[str], None] = ('20260207_add_observacoes', 'sprint8_security_lgpd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
