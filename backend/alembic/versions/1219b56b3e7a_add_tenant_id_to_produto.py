"""add tenant_id to produto

Revision ID: 1219b56b3e7a
Revises: d6d7829e3c17
Create Date: 2026-01-26 04:12:33.031626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1219b56b3e7a'
down_revision: Union[str, Sequence[str], None] = 'd6d7829e3c17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add tenant_id column as nullable first
    op.add_column(
        'produtos',
        sa.Column('tenant_id', postgresql.UUID(), nullable=True)
    )

    # Create index
    op.create_index(
        'ix_produtos_tenant_id',
        'produtos',
        ['tenant_id']
    )

    # Backfill with first tenant
    op.execute(
        """
        UPDATE produtos
        SET tenant_id = (
            SELECT id FROM tenants
            ORDER BY created_at
            LIMIT 1
        )
        """
    )

    # Make tenant_id not nullable
    op.alter_column(
        'produtos',
        'tenant_id',
        nullable=False
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_produtos_tenant',
        'produtos',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_produtos_tenant', 'produtos', type_='foreignkey')
    op.drop_index('ix_produtos_tenant_id', table_name='produtos')
    op.drop_column('produtos', 'tenant_id')
