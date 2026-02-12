"""create tenants table

Revision ID: 1e883f521a8c
Revises: b2761c83a5dd
Create Date: 2026-01-26 02:51:35.543134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e883f521a8c'
down_revision: Union[str, Sequence[str], None] = 'b2761c83a5dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy.dialects.postgresql import UUID
    import sqlalchemy as sa

    op.create_table(
        "tenants",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("plan", sa.String(length=50), nullable=False, server_default="free"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("tenants")