"""add_permite_estoque_negativo_to_tenant

Revision ID: 0e9ee2b0cca2
Revises: e8c8810a6193
Create Date: 2026-02-12 21:10:27.842998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e9ee2b0cca2'
down_revision: Union[str, Sequence[str], None] = 'e8c8810a6193'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adiciona coluna permite_estoque_negativo na tabela tenants
    op.add_column(
        'tenants',
        sa.Column('permite_estoque_negativo', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove coluna permite_estoque_negativo da tabela tenants
    op.drop_column('tenants', 'permite_estoque_negativo')
