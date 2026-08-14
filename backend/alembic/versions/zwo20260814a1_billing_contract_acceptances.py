"""add immutable billing contract acceptances

Revision ID: zwo20260814a1
Revises: zwn20260813a1
Create Date: 2026-08-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zwo20260814a1"
down_revision = "zwn20260813a1"
branch_labels = None
depends_on = None


TABLE_NAME = "billing_contract_acceptances"
IMMUTABILITY_FUNCTION = "reject_billing_contract_acceptance_mutation"
IMMUTABILITY_TRIGGER = "trg_billing_contract_acceptances_immutable"


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("acceptance_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("user_name", sa.String(length=255), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("user_role", sa.String(length=80), nullable=True),
        sa.Column("contractor_name", sa.String(length=255), nullable=False),
        sa.Column("contractor_tax_id", sa.String(length=20), nullable=True),
        sa.Column("contract_version", sa.String(length=50), nullable=False),
        sa.Column("terms_version", sa.String(length=50), nullable=False),
        sa.Column("privacy_version", sa.String(length=50), nullable=False),
        sa.Column("acceptance_text", sa.Text(), nullable=False),
        sa.Column("document_url", sa.String(length=255), nullable=False),
        sa.Column("terms_url", sa.String(length=255), nullable=False),
        sa.Column("privacy_url", sa.String(length=255), nullable=False),
        sa.Column("document_sha256", sa.String(length=64), nullable=False),
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
        sa.Column("billing_type", sa.String(length=30), nullable=False),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column(
            "provider", sa.String(length=30), nullable=False, server_default="asaas"
        ),
        sa.Column("provider_environment", sa.String(length=20), nullable=False),
        sa.Column("provider_subscription_id", sa.String(length=80), nullable=False),
        sa.Column(
            "channel", sa.String(length=20), nullable=False, server_default="web"
        ),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("client_timezone", sa.String(length=80), nullable=True),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("acceptance_id", name="uq_billing_contract_acceptance_id"),
    )
    for column_name in (
        "tenant_id",
        "user_id",
        "contract_version",
        "plan_code",
        "provider_subscription_id",
        "request_id",
        "accepted_at",
    ):
        op.create_index(
            f"ix_{TABLE_NAME}_{column_name}",
            TABLE_NAME,
            [column_name],
            unique=False,
        )

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(TABLE_NAME,),
        enable=True,
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            f"""
            CREATE OR REPLACE FUNCTION {IMMUTABILITY_FUNCTION}()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'billing contract acceptances are append-only';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {IMMUTABILITY_TRIGGER}
            BEFORE UPDATE OR DELETE ON {TABLE_NAME}
            FOR EACH ROW EXECUTE FUNCTION {IMMUTABILITY_FUNCTION}()
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"DROP TRIGGER IF EXISTS {IMMUTABILITY_TRIGGER} ON {TABLE_NAME}")
        op.execute(f"DROP FUNCTION IF EXISTS {IMMUTABILITY_FUNCTION}()")

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(TABLE_NAME,),
        enable=False,
    )
    op.drop_table(TABLE_NAME)
