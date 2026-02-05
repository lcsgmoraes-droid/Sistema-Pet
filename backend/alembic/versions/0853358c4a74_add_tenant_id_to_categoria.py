"""add tenant_id to categoria

Revision ID: 0853358c4a74
Revises: 1219b56b3e7a
Create Date: 2026-01-26 09:34:19.957084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0853358c4a74'
down_revision: Union[str, Sequence[str], None] = '1219b56b3e7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add tenant_id column as nullable first
    op.add_column(
        'categorias',
        sa.Column('tenant_id', postgresql.UUID(), nullable=True)
    )

    # Create index
    op.create_index(
        'ix_categorias_tenant_id',
        'categorias',
        ['tenant_id']
    )

    # Backfill with first tenant
    op.execute(
        """
        UPDATE categorias
        SET tenant_id = (
            SELECT id FROM tenants
            ORDER BY created_at
            LIMIT 1
        )
        """
    )

    # Make tenant_id not nullable
    op.alter_column(
        'categorias',
        'tenant_id',
        nullable=False
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_categorias_tenant',
        'categorias',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_categorias_tenant', 'categorias', type_='foreignkey')
    op.drop_index('ix_categorias_tenant_id', table_name='categorias')
    op.drop_column('categorias', 'tenant_id')
