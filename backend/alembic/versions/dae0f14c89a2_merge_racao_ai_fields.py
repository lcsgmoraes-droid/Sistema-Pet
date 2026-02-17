"""merge_racao_ai_fields

Revision ID: dae0f14c89a2
Revises: 20260214_add_racao_ai_fields, 673f25f32970
Create Date: 2026-02-14 03:34:55.031226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dae0f14c89a2'
down_revision: Union[str, Sequence[str], None] = '673f25f32970'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
