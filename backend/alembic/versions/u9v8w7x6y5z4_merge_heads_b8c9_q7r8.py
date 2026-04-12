"""merge heads b8c9 and q7r8

Revision ID: u9v8w7x6y5z4
Revises: b8c9d0e1f2a3, q7r8s9t0u1v2
Create Date: 2026-04-12 00:00:00.000000
"""

from typing import Sequence, Union


revision: str = "u9v8w7x6y5z4"
down_revision: Union[str, Sequence[str], None] = ("b8c9d0e1f2a3", "q7r8s9t0u1v2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration heads without schema changes."""
    pass


def downgrade() -> None:
    """No-op downgrade for merge migration."""
    pass
