"""merge stone pos and comissoes heads

Revision ID: 0f8a8df9259d
Revises: p1q2r3s4t5u6, pa20260526a1
Create Date: 2026-05-31 11:54:46.756716

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "0f8a8df9259d"
down_revision: Union[str, Sequence[str], None] = ("p1q2r3s4t5u6", "pa20260526a1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
