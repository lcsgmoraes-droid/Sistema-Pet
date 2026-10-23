"""Concessao FULL operacional independente da cobranca."""

from alembic import op
import sqlalchemy as sa

revision = "zzzzn20261023a1"
down_revision = "zzzzm20261020a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "manual_full_access",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "manual_full_access")
