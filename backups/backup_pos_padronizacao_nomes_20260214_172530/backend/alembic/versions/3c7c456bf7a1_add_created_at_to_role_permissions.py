"""add_created_at_to_role_permissions

Revision ID: 3c7c456bf7a1
Revises: 6855106d3e7e
Create Date: 2026-01-26 21:38:37.315659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c7c456bf7a1'
down_revision: Union[str, Sequence[str], None] = '6855106d3e7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('role_permissions', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    print("✅ Coluna created_at adicionada em role_permissions")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('role_permissions', 'created_at')
