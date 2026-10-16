"""ensure LGPD data access logs table

Revision ID: ny20260508a4
Revises: nx20260508a3
Create Date: 2026-05-08 17:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "ny20260508a4"
down_revision = "nx20260508a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("data_access_logs"):
        return

    op.create_table(
        "data_access_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("subject_type", sa.String(length=50), nullable=False),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column("accessed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("access_type", sa.String(length=50), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_access_log_tenant_time",
        "data_access_logs",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_access_log_subject",
        "data_access_logs",
        ["subject_id", "subject_type"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("data_access_logs"):
        return

    op.drop_index("ix_access_log_subject", table_name="data_access_logs")
    op.drop_index("ix_access_log_tenant_time", table_name="data_access_logs")
    op.drop_table("data_access_logs")
