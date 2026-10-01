"""Comprovantes de pagamento privados com revisao humana.

Revision ID: zzza20261001a1
Revises: zzz20260930a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zzza20261001a1"
down_revision = "zzz20260930a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_payment_proofs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider_payment_id", sa.String(80), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("filename", sa.String(180), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("reviewer_admin_id", sa.Integer(), sa.ForeignKey("platform_admins.id"), nullable=True),
        sa.Column("review_note", sa.String(1000), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_billing_payment_proofs_tenant_id", "billing_payment_proofs", ["tenant_id"])
    op.create_index("ix_billing_payment_proofs_status", "billing_payment_proofs", ["status"])
    op.create_index("ix_billing_payment_proofs_provider_payment_id", "billing_payment_proofs", ["provider_payment_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE billing_payment_proofs ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE billing_payment_proofs FORCE ROW LEVEL SECURITY")
        guard = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
        op.execute(
            "CREATE POLICY billing_payment_proofs_tenant_isolation "
            f"ON billing_payment_proofs USING ({guard}) WITH CHECK ({guard})"
        )


def downgrade() -> None:
    op.drop_index("ix_billing_payment_proofs_provider_payment_id", table_name="billing_payment_proofs")
    op.drop_index("ix_billing_payment_proofs_status", table_name="billing_payment_proofs")
    op.drop_index("ix_billing_payment_proofs_tenant_id", table_name="billing_payment_proofs")
    op.drop_table("billing_payment_proofs")
