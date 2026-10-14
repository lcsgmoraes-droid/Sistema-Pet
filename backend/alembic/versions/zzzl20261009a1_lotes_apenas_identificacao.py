"""Distingue identificação de lotes sem movimento do estoque.

Revision ID: zzzl20261009a1
Revises: zzzk20261009a1
"""

from alembic import op
import sqlalchemy as sa

revision = "zzzl20261009a1"
down_revision = "zzzk20261009a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "produto_lotes",
        sa.Column("apenas_identificacao", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("produto_lotes", "apenas_identificacao")
