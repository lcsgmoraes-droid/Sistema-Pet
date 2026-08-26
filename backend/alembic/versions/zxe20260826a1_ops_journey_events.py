"""add sanitized journey events for SLO measurement

Revision ID: zxe20260826a1
Revises: zxd20260826a1
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zxe20260826a1"
down_revision = "zxd20260826a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ops_journey_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_key", sa.String(length=96), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("journey", sa.String(length=80), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.Column("operation_id", sa.String(length=96), nullable=False),
        sa.Column("method", sa.String(length=12), nullable=False),
        sa.Column("path_template", sa.String(length=180), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=True),
        sa.Column(
            "source",
            sa.String(length=60),
            server_default="request_context",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )
    op.create_index(
        "ix_ops_journey_events_created_at",
        "ops_journey_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_event_key",
        "ops_journey_events",
        ["event_key"],
        unique=True,
    )
    op.create_index(
        "ix_ops_journey_events_journey",
        "ops_journey_events",
        ["journey"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_journey_created",
        "ops_journey_events",
        ["journey", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_operation_id",
        "ops_journey_events",
        ["operation_id"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_outcome",
        "ops_journey_events",
        ["outcome"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_outcome_created",
        "ops_journey_events",
        ["outcome", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_path_template",
        "ops_journey_events",
        ["path_template"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_provider",
        "ops_journey_events",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_request_id",
        "ops_journey_events",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_tenant_id",
        "ops_journey_events",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_ops_journey_events_tenant_journey_created",
        "ops_journey_events",
        ["tenant_id", "journey", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("ops_journey_events")
