"""make clientes.tenant_id not null

Revision ID: f625dfeb4b53
Revises: 799f82d6d017
Create Date: 2026-01-26 03:34:34.831850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'f625dfeb4b53'
down_revision: Union[str, Sequence[str], None] = '799f82d6d017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make tenant_id NOT NULL to enforce multi-tenant isolation."""
    op.alter_column(
        "clientes",
        "tenant_id",
        existing_type=UUID(as_uuid=True),
        nullable=False
    )


def downgrade() -> None:
    """Revert tenant_id to nullable."""
    op.alter_column(
        "clientes",
        "tenant_id",
        existing_type=UUID(as_uuid=True),
        nullable=True
    )
