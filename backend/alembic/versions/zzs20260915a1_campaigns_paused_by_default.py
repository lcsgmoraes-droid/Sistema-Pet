"""Inicia novas campanhas pausadas por seguranca.

Revision ID: zzs20260915a1
Revises: zzr20260915a1
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "zzs20260915a1"
down_revision = "zzr20260915a1"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "campaigns",
        "status",
        existing_type=sa.Enum(
            "active",
            "paused",
            "archived",
            name="campaign_status_enum",
        ),
        server_default=sa.text("'paused'::campaign_status_enum"),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "campaigns",
        "status",
        existing_type=sa.Enum(
            "active",
            "paused",
            "archived",
            name="campaign_status_enum",
        ),
        server_default=sa.text("'active'::campaign_status_enum"),
        existing_nullable=False,
    )
