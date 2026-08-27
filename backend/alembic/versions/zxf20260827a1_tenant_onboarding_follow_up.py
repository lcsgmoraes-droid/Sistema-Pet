"""add tenant onboarding follow-up fields

Revision ID: zxf20260827a1
Revises: zxe20260826a1
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "zxf20260827a1"
down_revision = "zxe20260826a1"
branch_labels = None
depends_on = None


SATISFACTION_CHECK = (
    "onboarding_satisfaction IN "
    "('not_collected', 'satisfied', 'neutral', 'dissatisfied')"
)


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("onboarding_owner_name", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("onboarding_unblocked_on", sa.Date(), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "onboarding_satisfaction",
            sa.String(length=24),
            server_default="not_collected",
            nullable=False,
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "onboarding_follow_up_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_tenants_onboarding_satisfaction",
        "tenants",
        SATISFACTION_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_tenants_onboarding_satisfaction",
        "tenants",
        type_="check",
    )
    op.drop_column("tenants", "onboarding_follow_up_updated_at")
    op.drop_column("tenants", "onboarding_satisfaction")
    op.drop_column("tenants", "onboarding_unblocked_on")
    op.drop_column("tenants", "onboarding_owner_name")
