"""merge heads c7d8 and f1e2

Revision ID: a7b8c9d0e1f2
Revises: c7d8e9f0a1b2, f1e2d3c4b5a6
Create Date: 2026-03-28 15:33:00.000000
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = ("c7d8e9f0a1b2", "f1e2d3c4b5a6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
