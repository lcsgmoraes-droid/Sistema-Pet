"""add_missing_columns_to_rotas_entrega_paradas

Revision ID: 20260216_fix_paradas
Revises: 20260216_fix_rotas_entrega
Create Date: 2026-02-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import NUMERIC


# revision identifiers, used by Alembic.
revision: str = '20260216_fix_paradas'
down_revision: Union[str, Sequence[str], None] = '20260216_fix_rotas_entrega'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to rotas_entrega_paradas table."""
    
    # Add status column
    op.add_column(
        'rotas_entrega_paradas',
        sa.Column('status', sa.String(20), nullable=False, server_default='pendente')
    )
    
    # Create index for status
    op.create_index('ix_rotas_entrega_paradas_status', 'rotas_entrega_paradas', ['status'])
    
    # Add data_entrega column
    op.add_column(
        'rotas_entrega_paradas',
        sa.Column('data_entrega', sa.DateTime(), nullable=True)
    )
    
    # Add km_entrega column
    op.add_column(
        'rotas_entrega_paradas',
        sa.Column('km_entrega', NUMERIC(10, 2), nullable=True)
    )


def downgrade() -> None:
    """Remove added columns from rotas_entrega_paradas table."""
    op.drop_column('rotas_entrega_paradas', 'km_entrega')
    op.drop_column('rotas_entrega_paradas', 'data_entrega')
    op.drop_index('ix_rotas_entrega_paradas_status', 'rotas_entrega_paradas')
    op.drop_column('rotas_entrega_paradas', 'status')
