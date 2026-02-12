"""add tenant_id to pets

Revision ID: 93f568f1ffb5
Revises: f625dfeb4b53
Create Date: 2026-01-26 03:40:21.193895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '93f568f1ffb5'
down_revision: Union[str, Sequence[str], None] = 'f625dfeb4b53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tenant_id column to pets table."""
    op.add_column(
        "pets",
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True)
    )

    op.create_foreign_key(
        "fk_pets_tenant",
        "pets",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT"
    )

    op.create_index(
        "ix_pets_tenant_id",
        "pets",
        ["tenant_id"]
    )


def downgrade() -> None:
    """Remove tenant_id column from pets table."""
    op.drop_index("ix_pets_tenant_id", table_name="pets")
    op.drop_constraint("fk_pets_tenant", "pets", type_="foreignkey")
    op.drop_column("pets", "tenant_id")
