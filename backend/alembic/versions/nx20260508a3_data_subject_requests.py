"""create data subject request workflow

Revision ID: nx20260508a3
Revises: nw20260508a2
Create Date: 2026-05-08 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "nx20260508a3"
down_revision = "nw20260508a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("data_subject_requests"):
        return

    op.create_table(
        "data_subject_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=50), nullable=False),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column(
            "status", sa.String(length=30), nullable=False, server_default="pending"
        ),
        sa.Column("requester_name", sa.String(length=255), nullable=True),
        sa.Column("requester_email", sa.String(length=255), nullable=True),
        sa.Column("requester_phone", sa.String(length=50), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("request_payload", sa.Text(), nullable=True),
        sa.Column("response_payload", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("processed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_subject_requests_tenant_status",
        "data_subject_requests",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_data_subject_requests_subject",
        "data_subject_requests",
        ["tenant_id", "subject_type", "subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_data_subject_requests_type",
        "data_subject_requests",
        ["request_type"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("data_subject_requests"):
        return

    op.drop_index("ix_data_subject_requests_type", table_name="data_subject_requests")
    op.drop_index(
        "ix_data_subject_requests_subject", table_name="data_subject_requests"
    )
    op.drop_index(
        "ix_data_subject_requests_tenant_status", table_name="data_subject_requests"
    )
    op.drop_table("data_subject_requests")
