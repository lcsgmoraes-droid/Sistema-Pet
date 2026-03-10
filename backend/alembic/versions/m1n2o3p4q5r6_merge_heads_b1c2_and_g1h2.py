"""merge heads b1c2 and g1h2

Revision ID: m1n2o3p4q5r6
Revises: b1c2d3e4f5a6, g1h2i3j4k5l6
Create Date: 2026-03-10 00:00:00.000000

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "m1n2o3p4q5r6"
down_revision: Union[str, Sequence[str], None] = (
    "b1c2d3e4f5a6",
    "g1h2i3j4k5l6",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration heads without schema changes."""
    pass


def downgrade() -> None:
    """No-op downgrade for merge migration."""
    pass
