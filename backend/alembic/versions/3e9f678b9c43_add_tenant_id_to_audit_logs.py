"""add tenant_id to audit_logs

Revision ID: 3e9f678b9c43
Revises: 2d87cec25bcc
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3e9f678b9c43"
down_revision = "2d87cec25bcc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "audit_logs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_index(
        "ix_audit_logs_tenant_id",
        "audit_logs",
        ["tenant_id"],
    )

    op.create_foreign_key(
        "fk_audit_logs_tenant_id",
        "audit_logs",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint(
        "fk_audit_logs_tenant_id",
        "audit_logs",
        type_="foreignkey",
    )
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_column("audit_logs", "tenant_id")
