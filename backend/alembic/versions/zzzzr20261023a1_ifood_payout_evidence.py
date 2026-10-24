"""DEV payout snapshots and cached reconciliation requests.

Revision ID: zzzzr20261023a1
Revises: zzzzq20261023a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzr20261023a1"
down_revision = "zzzzq20261023a1"
branch_labels = None
depends_on = None


def base():
    return [
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade():
    op.create_table(
        "ifood_payout_snapshots",
        *base(),
        sa.Column("merchant_id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("basis", sa.String(20), nullable=False),
        sa.Column("begin_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "kind",
            "basis",
            "begin_date",
            "end_date",
            "revision",
            name="uq_ifood_payout_revision",
        ),
        sa.CheckConstraint(
            "kind IN ('settlements','statement')", name="ck_ifood_payout_kind"
        ),
        sa.CheckConstraint(
            "basis IN ('calculation','payment','competence')",
            name="ck_ifood_payout_basis",
        ),
        sa.CheckConstraint("mode = 'homologation'", name="ck_ifood_payout_mode"),
        sa.CheckConstraint(
            "revision > 0 AND end_date >= begin_date", name="ck_ifood_payout_period"
        ),
    )
    op.create_index(
        "uq_ifood_payout_current",
        "ifood_payout_snapshots",
        ["tenant_id", "merchant_id", "mode", "kind", "basis", "begin_date", "end_date"],
        unique=True,
        postgresql_where=sa.text("active = true"),
        sqlite_where=sa.text("active = 1"),
    )
    op.create_table(
        "ifood_reconciliation_jobs",
        *base(),
        sa.Column("merchant_id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("competence", sa.String(7), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported", sa.Boolean(), nullable=False),
        sa.Column("last_error", sa.String(250), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "competence",
            name="uq_ifood_recon_job_scope",
        ),
        sa.CheckConstraint("mode = 'homologation'", name="ck_ifood_recon_job_mode"),
        sa.CheckConstraint("attempts >= 0", name="ck_ifood_recon_attempts"),
    )
    for table in ("ifood_payout_snapshots", "ifood_reconciliation_jobs"):
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        apply_tenant_rls(op_module=op, sa_module=sa, table_names=(table,), enable=True)


def downgrade():
    op.drop_table("ifood_reconciliation_jobs")
    op.drop_table("ifood_payout_snapshots")
