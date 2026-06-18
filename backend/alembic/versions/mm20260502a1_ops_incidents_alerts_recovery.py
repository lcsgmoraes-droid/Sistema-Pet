"""create ops incident, alert and recovery tables

Revision ID: mm20260502a1
Revises: ll20260430a1
Create Date: 2026-05-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "mm20260502a1"
down_revision = "ll20260430a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ops_error_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_key", sa.String(length=96), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.String(length=80), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.Column("method", sa.String(length=12), nullable=True),
        sa.Column("path", sa.String(length=600), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("exception_type", sa.String(length=160), nullable=True),
        sa.Column("exception_message", sa.Text(), nullable=True),
        sa.Column("client_ip", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("source", sa.String(length=60), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )
    op.create_index(op.f("ix_ops_error_events_created_at"), "ops_error_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_ops_error_events_event_key"), "ops_error_events", ["event_key"], unique=False)
    op.create_index(op.f("ix_ops_error_events_path"), "ops_error_events", ["path"], unique=False)
    op.create_index(op.f("ix_ops_error_events_request_id"), "ops_error_events", ["request_id"], unique=False)
    op.create_index(op.f("ix_ops_error_events_status_code"), "ops_error_events", ["status_code"], unique=False)
    op.create_index(op.f("ix_ops_error_events_tenant_id"), "ops_error_events", ["tenant_id"], unique=False)
    op.create_index("ix_ops_error_events_path_created", "ops_error_events", ["path", "created_at"], unique=False)
    op.create_index("ix_ops_error_events_status_created", "ops_error_events", ["status_code", "created_at"], unique=False)
    op.create_index("ix_ops_error_events_tenant_created", "ops_error_events", ["tenant_id", "created_at"], unique=False)

    op.create_table(
        "ops_alerts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("alert_key", sa.String(length=180), nullable=False),
        sa.Column("scope", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_name", sa.String(length=255), nullable=True),
        sa.Column("path", sa.String(length=600), nullable=True),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_key"),
    )
    op.create_index(op.f("ix_ops_alerts_alert_key"), "ops_alerts", ["alert_key"], unique=False)
    op.create_index(op.f("ix_ops_alerts_kind"), "ops_alerts", ["kind"], unique=False)
    op.create_index(op.f("ix_ops_alerts_last_seen_at"), "ops_alerts", ["last_seen_at"], unique=False)
    op.create_index(op.f("ix_ops_alerts_path"), "ops_alerts", ["path"], unique=False)
    op.create_index(op.f("ix_ops_alerts_request_id"), "ops_alerts", ["request_id"], unique=False)
    op.create_index(op.f("ix_ops_alerts_scope"), "ops_alerts", ["scope"], unique=False)
    op.create_index(op.f("ix_ops_alerts_severity"), "ops_alerts", ["severity"], unique=False)
    op.create_index(op.f("ix_ops_alerts_status"), "ops_alerts", ["status"], unique=False)
    op.create_index(op.f("ix_ops_alerts_tenant_id"), "ops_alerts", ["tenant_id"], unique=False)
    op.create_index("ix_ops_alerts_last_seen", "ops_alerts", ["last_seen_at"], unique=False)
    op.create_index("ix_ops_alerts_status_severity", "ops_alerts", ["status", "severity"], unique=False)
    op.create_index("ix_ops_alerts_tenant_status", "ops_alerts", ["tenant_id", "status"], unique=False)

    op.create_table(
        "ops_recovery_actions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("action_key", sa.String(length=160), nullable=False),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source_event_type", sa.String(length=80), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("uvicorn_pid", sa.Integer(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("action_key"),
    )
    op.create_index(op.f("ix_ops_recovery_actions_action_key"), "ops_recovery_actions", ["action_key"], unique=False)
    op.create_index(op.f("ix_ops_recovery_actions_action_type"), "ops_recovery_actions", ["action_type"], unique=False)
    op.create_index(op.f("ix_ops_recovery_actions_created_at"), "ops_recovery_actions", ["created_at"], unique=False)
    op.create_index(op.f("ix_ops_recovery_actions_source_event_type"), "ops_recovery_actions", ["source_event_type"], unique=False)
    op.create_index(op.f("ix_ops_recovery_actions_status"), "ops_recovery_actions", ["status"], unique=False)
    op.create_index("ix_ops_recovery_actions_status_created", "ops_recovery_actions", ["status", "created_at"], unique=False)
    op.create_index("ix_ops_recovery_actions_type_created", "ops_recovery_actions", ["action_type", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ops_recovery_actions_type_created", table_name="ops_recovery_actions")
    op.drop_index("ix_ops_recovery_actions_status_created", table_name="ops_recovery_actions")
    op.drop_index(op.f("ix_ops_recovery_actions_status"), table_name="ops_recovery_actions")
    op.drop_index(op.f("ix_ops_recovery_actions_source_event_type"), table_name="ops_recovery_actions")
    op.drop_index(op.f("ix_ops_recovery_actions_created_at"), table_name="ops_recovery_actions")
    op.drop_index(op.f("ix_ops_recovery_actions_action_type"), table_name="ops_recovery_actions")
    op.drop_index(op.f("ix_ops_recovery_actions_action_key"), table_name="ops_recovery_actions")
    op.drop_table("ops_recovery_actions")

    op.drop_index("ix_ops_alerts_tenant_status", table_name="ops_alerts")
    op.drop_index("ix_ops_alerts_status_severity", table_name="ops_alerts")
    op.drop_index("ix_ops_alerts_last_seen", table_name="ops_alerts")
    op.drop_index(op.f("ix_ops_alerts_tenant_id"), table_name="ops_alerts")
    op.drop_index(op.f("ix_ops_alerts_status"), table_name="ops_alerts")
    op.drop_index(op.f("ix_ops_alerts_severity"), table_name="ops_alerts")
    op.drop_index(op.f("ix_ops_alerts_scope"), table_name="ops_alerts")
    op.drop_index(op.f("ix_ops_alerts_request_id"), table_name="ops_alerts")
    op.drop_index(op.f("ix_ops_alerts_path"), table_name="ops_alerts")
    op.drop_index(op.f("ix_ops_alerts_last_seen_at"), table_name="ops_alerts")
    op.drop_index(op.f("ix_ops_alerts_kind"), table_name="ops_alerts")
    op.drop_index(op.f("ix_ops_alerts_alert_key"), table_name="ops_alerts")
    op.drop_table("ops_alerts")

    op.drop_index("ix_ops_error_events_tenant_created", table_name="ops_error_events")
    op.drop_index("ix_ops_error_events_status_created", table_name="ops_error_events")
    op.drop_index("ix_ops_error_events_path_created", table_name="ops_error_events")
    op.drop_index(op.f("ix_ops_error_events_tenant_id"), table_name="ops_error_events")
    op.drop_index(op.f("ix_ops_error_events_status_code"), table_name="ops_error_events")
    op.drop_index(op.f("ix_ops_error_events_request_id"), table_name="ops_error_events")
    op.drop_index(op.f("ix_ops_error_events_path"), table_name="ops_error_events")
    op.drop_index(op.f("ix_ops_error_events_event_key"), table_name="ops_error_events")
    op.drop_index(op.f("ix_ops_error_events_created_at"), table_name="ops_error_events")
    op.drop_table("ops_error_events")
