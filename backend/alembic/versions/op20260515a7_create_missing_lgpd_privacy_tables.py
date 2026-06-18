"""create missing LGPD privacy tables

Revision ID: op20260515a7
Revises: oo20260515a6
Create Date: 2026-05-15 18:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "op20260515a7"
down_revision = "oo20260515a6"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if index_name not in _index_names(table_name):
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    tables = _table_names()

    if "data_privacy_consents" not in tables:
        op.create_table(
            "data_privacy_consents",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.String(), nullable=False),
            sa.Column("subject_type", sa.String(length=50), nullable=False),
            sa.Column("subject_id", sa.String(length=255), nullable=False),
            sa.Column("phone_number", sa.String(length=20), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("consent_type", sa.String(length=100), nullable=False),
            sa.Column("consent_given", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("consent_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("revoke_reason", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing(
        "ix_data_privacy_consents_subject",
        "data_privacy_consents",
        ["tenant_id", "subject_type", "subject_id"],
    )
    _create_index_if_missing(
        "ix_data_privacy_consents_type",
        "data_privacy_consents",
        ["tenant_id", "consent_type"],
    )

    if "data_deletion_requests" not in tables:
        op.create_table(
            "data_deletion_requests",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.String(), nullable=False),
            sa.Column("subject_type", sa.String(length=50), nullable=False),
            sa.Column("subject_id", sa.String(length=255), nullable=False),
            sa.Column("request_date", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("processed_by_user_id", sa.Integer(), nullable=True),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("contact_phone", sa.String(length=20), nullable=True),
            sa.Column("contact_email", sa.String(length=255), nullable=True),
            sa.Column("extra_metadata", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing(
        "ix_data_deletion_requests_subject",
        "data_deletion_requests",
        ["tenant_id", "subject_type", "subject_id"],
    )
    _create_index_if_missing(
        "ix_data_deletion_requests_status",
        "data_deletion_requests",
        ["tenant_id", "status"],
    )

    if "security_audit_logs" not in tables:
        op.create_table(
            "security_audit_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.String(), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="info"),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("resource_type", sa.String(length=100), nullable=True),
            sa.Column("resource_id", sa.String(length=255), nullable=True),
            sa.Column("action", sa.String(length=100), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("extra_data", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing(
        "ix_security_audit_logs_tenant_time",
        "security_audit_logs",
        ["tenant_id", "created_at"],
    )
    _create_index_if_missing(
        "ix_security_audit_logs_event",
        "security_audit_logs",
        ["tenant_id", "event_type"],
    )


def downgrade() -> None:
    # Repair migration: keep downgrade non-destructive so an accidental rollback
    # does not remove operational LGPD/audit data from environments that already
    # had these tables before this revision.
    return
