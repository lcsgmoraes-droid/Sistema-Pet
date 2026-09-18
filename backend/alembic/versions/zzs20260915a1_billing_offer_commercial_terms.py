"""Registra as condicoes comerciais especificas da proposta.

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
    op.add_column(
        "billing_offers",
        sa.Column(
            "commercial_terms_json",
            sa.Text(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade():
    op.drop_column("billing_offers", "commercial_terms_json")
