"""make pets.tenant_id not null

Revision ID: d6d7829e3c17
Revises: 93f568f1ffb5
Create Date: 2026-01-26 03:44:39.053672

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "d6d7829e3c17"
down_revision = "93f568f1ffb5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "pets",
        "tenant_id",
        existing_type=UUID(as_uuid=True),
        nullable=False
    )


def downgrade() -> None:
    op.alter_column(
        "pets",
        "tenant_id",
        existing_type=UUID(as_uuid=True),
        nullable=True
    )
