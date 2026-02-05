"""Expand alembic_version column

Revision ID: expand_version_num
Revises: 1a1f49b0ebae
Create Date: 2026-01-27

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'expand_version'
down_revision = '1a1f49b0ebae'
branch_labels = None
depends_on = None


def upgrade():
    """Expande alembic_version.version_num para VARCHAR(64)"""
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")


def downgrade():
    """Reverte para VARCHAR(32)"""
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)")
