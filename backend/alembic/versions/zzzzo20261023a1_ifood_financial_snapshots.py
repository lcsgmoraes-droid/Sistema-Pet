"""Snapshots financeiros iFood e versoes de custos informados por pedido."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzo20261023a1"
down_revision = "zzzzn20261023a1"
branch_labels = None
depends_on = None

TABLE_NAMES = (
    "ifood_financial_snapshots",
    "ifood_financial_events",
    "ifood_financial_order_costs",
)


def _tenant_columns():
    return [
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
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
        "ifood_financial_snapshots",
        *_tenant_columns(),
        sa.Column("merchant_id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("begin_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_ifood_fin_snapshot_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "begin_date",
            "end_date",
            "revision",
            name="uq_ifood_fin_snapshot_revision",
        ),
        sa.CheckConstraint(
            "end_date >= begin_date", name="ck_ifood_fin_snapshot_period"
        ),
        sa.CheckConstraint("revision > 0", name="ck_ifood_fin_snapshot_revision"),
    )
    op.create_index(
        "uq_ifood_fin_snapshot_current",
        "ifood_financial_snapshots",
        ["tenant_id", "merchant_id", "mode", "begin_date", "end_date"],
        unique=True,
        postgresql_where=sa.text("active = true"),
        sqlite_where=sa.text("active = 1"),
    )
    op.create_table(
        "ifood_financial_events",
        *_tenant_columns(),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.String(80), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("trigger", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("has_transfer_impact", sa.Boolean(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "snapshot_id"],
            ["ifood_financial_snapshots.tenant_id", "ifood_financial_snapshots.id"],
            name="fk_ifood_fin_event_tenant_snapshot",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "snapshot_id", "position", name="uq_ifood_fin_event_position"
        ),
        sa.CheckConstraint("position > 0", name="ck_ifood_fin_event_position"),
    )
    op.create_index(
        "ix_ifood_fin_event_order", "ifood_financial_events", ["tenant_id", "order_id"]
    )
    op.create_table(
        "ifood_financial_order_costs",
        *_tenant_columns(),
        sa.Column("merchant_id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("order_id", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *(
            sa.Column(field, sa.Numeric(18, 2), nullable=True)
            for field in ("revenue", "cmv", "tax", "other_costs")
        ),
        sa.Column("source_note", sa.String(1000), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "order_id",
            "version",
            name="uq_ifood_fin_order_cost_version",
        ),
        sa.CheckConstraint("version > 0", name="ck_ifood_fin_cost_version"),
        *(
            sa.CheckConstraint(
                f"{field} IS NULL OR {field} >= 0", name=f"ck_ifood_fin_{field}"
            )
            for field in ("revenue", "cmv", "tax", "other_costs")
        ),
    )
    op.create_index(
        "ix_ifood_fin_order_cost_scope",
        "ifood_financial_order_costs",
        ["tenant_id", "merchant_id", "mode", "order_id"],
    )
    for table in TABLE_NAMES:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=TABLE_NAMES, enable=True)


def downgrade():
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=TABLE_NAMES, enable=False)
    for table in reversed(TABLE_NAMES):
        op.drop_table(table)
