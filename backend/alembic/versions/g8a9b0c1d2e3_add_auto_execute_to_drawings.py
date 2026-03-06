"""add auto_execute to drawings

Revision ID: g8a9b0c1d2e3
Revises: f7a8b9c0d1e2
Create Date: 2026-03-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'g8a9b0c1d2e3'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'drawings',
        sa.Column('auto_execute', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade():
    op.drop_column('drawings', 'auto_execute')
