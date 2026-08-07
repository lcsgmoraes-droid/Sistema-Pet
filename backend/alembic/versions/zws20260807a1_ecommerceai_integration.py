"""add CorePet EcommerceAI integration

Revision ID: zws20260807a1
Revises: zwr20260801a1
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zws20260807a1"
down_revision = "zwr20260801a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ecommerceai_connection_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("request_nonce", sa.String(80), nullable=False),
        sa.Column("client_id", sa.String(80), nullable=False),
        sa.Column("ecommerceai_user_id", sa.String(80), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=True),
        sa.Column("account_email", sa.String(255), nullable=True),
        sa.Column("callback_url", sa.String(1000), nullable=False),
        sa.Column("state", sa.String(255), nullable=False),
        sa.Column(
            "requested_scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "approved_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("callback_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("request_id"),
        sa.UniqueConstraint("request_nonce"),
        sa.UniqueConstraint("state"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_connection_requests_request_id",
        "ecommerceai_connection_requests",
        ["request_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_connection_requests_user",
        "ecommerceai_connection_requests",
        ["ecommerceai_user_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_connection_requests_status",
        "ecommerceai_connection_requests",
        ["status"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_connection_requests_tenant",
        "ecommerceai_connection_requests",
        ["tenant_id"],
        if_not_exists=True,
    )

    op.create_table(
        "ecommerceai_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ecommerceai_user_id", sa.String(80), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=True),
        sa.Column("account_email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("token_prefix", sa.String(20), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_catalog_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["ecommerceai_connection_requests.request_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("request_id", name="uq_ecommerceai_connections_request"),
        sa.UniqueConstraint("token_hash"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_connections_public_id",
        "ecommerceai_connections",
        ["public_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_connections_tenant",
        "ecommerceai_connections",
        ["tenant_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_connections_user",
        "ecommerceai_connections",
        ["ecommerceai_user_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_connections_token_hash",
        "ecommerceai_connections",
        ["token_hash"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_connections_tenant_status",
        "ecommerceai_connections",
        ["tenant_id", "status"],
        if_not_exists=True,
    )

    op.create_table(
        "ecommerceai_inbound_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(80), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("schema_version", sa.String(20), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "processed_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["ecommerceai_connections.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "connection_id", "event_id", name="uq_ecommerceai_inbound_connection_event"
        ),
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_inbound_tenant",
        "ecommerceai_inbound_events",
        ["tenant_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_inbound_tenant_received",
        "ecommerceai_inbound_events",
        ["tenant_id", "received_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ecommerceai_inbound_tenant_type",
        "ecommerceai_inbound_events",
        ["tenant_id", "event_type"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ecommerceai_inbound_events CASCADE")
    op.execute("DROP TABLE IF EXISTS ecommerceai_connections CASCADE")
    op.execute("DROP TABLE IF EXISTS ecommerceai_connection_requests CASCADE")
