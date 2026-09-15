"""Registra as condicoes comerciais especificas da proposta.

Revision ID: zzq20260914a1
Revises: zzp20260914a1
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa

revision = "zzq20260914a1"
down_revision = "zzp20260914a1"
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
