"""adiciona email de resposta por empresa

Revision ID: zzc20260903a1
Revises: zzb20260903a1
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa

revision = "zzc20260903a1"
down_revision = "zzb20260903a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants", sa.Column("email_resposta", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("tenants", "email_resposta")
