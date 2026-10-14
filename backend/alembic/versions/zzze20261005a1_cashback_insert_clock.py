"""Record cashback INSERT time and original credit of restored lots.

Revision ID: zzze20261005a1
Revises: zzzd20261003a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zzze20261005a1"
down_revision = "zzzd20261003a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL now() is fixed at transaction start. A later cashback INSERT
    # can consequently appear to precede a credit committed in the meantime.
    op.alter_column(
        "cashback_transactions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=sa.text("clock_timestamp()"),
    )
    op.add_column(
        "cashback_transactions",
        sa.Column("origin_credit_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_ct_tenant_customer_origin_credit",
        "cashback_transactions",
        ["tenant_id", "customer_id", "origin_credit_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ct_tenant_customer_origin_credit",
        table_name="cashback_transactions",
    )
    op.drop_column("cashback_transactions", "origin_credit_id")
    op.alter_column(
        "cashback_transactions",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=sa.text("now()"),
    )
