"""add updated_at to user_sessions

Revision ID: 2d87cec25bcc
Revises: 4d8e567a8f92
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2d87cec25bcc"
down_revision = "4d8e567a8f92"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_sessions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("user_sessions", "updated_at")
