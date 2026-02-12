"""add tenant_id and role to users

Revision ID: 1c12bfb8d1bf
Revises: 1e883f521a8c
Create Date: 2026-01-26 02:55:39.741671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c12bfb8d1bf'
down_revision: Union[str, Sequence[str], None] = '1e883f521a8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy.dialects.postgresql import UUID
    import sqlalchemy as sa

    op.add_column(
        "users",
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True)
    )

    op.add_column(
        "users",
        sa.Column("role", sa.String(length=50), nullable=True)
    )

    op.create_foreign_key(
        "fk_users_tenant",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT"
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_users_tenant", "users", type_="foreignkey")
    op.drop_column("users", "role")
    op.drop_column("users", "tenant_id")