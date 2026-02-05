"""add tenant_id to clientes

Revision ID: 799f82d6d017
Revises: 1c12bfb8d1bf
Create Date: 2026-01-26 03:29:00.174337

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '799f82d6d017'
down_revision: Union[str, Sequence[str], None] = '1c12bfb8d1bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tenant_id column to clientes table."""
    # Add tenant_id column as NULLABLE initially
    op.add_column(
        "clientes",
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    
    # Create foreign key constraint
    op.create_foreign_key(
        "fk_clientes_tenant",
        "clientes",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    
    # Create index for better query performance
    op.create_index(
        "ix_clientes_tenant_id",
        "clientes",
        ["tenant_id"],
    )


def downgrade() -> None:
    """Remove tenant_id column from clientes table."""
    # Drop index first
    op.drop_index("ix_clientes_tenant_id", table_name="clientes")
    
    # Drop foreign key constraint
    op.drop_constraint("fk_clientes_tenant", "clientes", type_="foreignkey")
    
    # Drop column
    op.drop_column("clientes", "tenant_id")
