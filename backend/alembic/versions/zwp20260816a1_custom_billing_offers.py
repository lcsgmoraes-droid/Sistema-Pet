"""add custom billing offers with public acceptance links

Revision ID: zwp20260816a1
Revises: zwo20260814a1
Create Date: 2026-08-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "zwp20260816a1"
down_revision = "zwo20260814a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_offers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_reference", sa.String(length=36), nullable=False),
        sa.Column("token_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("plan_code", sa.String(length=50), nullable=False),
        sa.Column("plan_name", sa.String(length=120), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="BRL"
        ),
        sa.Column(
            "billing_cycle",
            sa.String(length=20),
            nullable=False,
            server_default="MONTHLY",
        ),
        sa.Column(
            "billing_type",
            sa.String(length=30),
            nullable=False,
            server_default="UNDEFINED",
        ),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("extra_modules_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="ready"
        ),
        sa.Column("payment_status", sa.String(length=40), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("representative_name", sa.String(length=255), nullable=True),
        sa.Column("representative_email", sa.String(length=255), nullable=True),
        sa.Column("representative_role", sa.String(length=120), nullable=True),
        sa.Column(
            "provider", sa.String(length=30), nullable=False, server_default="asaas"
        ),
        sa.Column("provider_environment", sa.String(length=20), nullable=True),
        sa.Column("provider_customer_id", sa.String(length=80), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=80), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=80), nullable=True),
        sa.Column("checkout_url", sa.String(length=500), nullable=True),
        sa.Column(
            "revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offer_id"),
        sa.UniqueConstraint("token_sha256"),
    )
    for column_name in (
        "tenant_reference",
        "plan_code",
        "status",
        "provider_subscription_id",
        "provider_payment_id",
    ):
        op.create_index(
            f"ix_billing_offers_{column_name}",
            "billing_offers",
            [column_name],
            unique=False,
        )

    op.alter_column(
        "billing_contract_acceptances",
        "user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "billing_contract_acceptances",
        sa.Column("billing_offer_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_billing_contract_acceptances_offer",
        "billing_contract_acceptances",
        "billing_offers",
        ["billing_offer_id"],
        ["offer_id"],
    )
    op.create_index(
        "ix_billing_contract_acceptances_billing_offer_id",
        "billing_contract_acceptances",
        ["billing_offer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_billing_contract_acceptances_billing_offer_id",
        table_name="billing_contract_acceptances",
    )
    op.drop_constraint(
        "fk_billing_contract_acceptances_offer",
        "billing_contract_acceptances",
        type_="foreignkey",
    )
    op.drop_column("billing_contract_acceptances", "billing_offer_id")
    # Public acceptances have no internal CorePet user. Keep this column nullable
    # on rollback so the append-only legal records remain intact and attributable
    # to the representative captured in the immutable snapshot.
    op.drop_table("billing_offers")
