"""create bling flow monitor tables

Revision ID: f1e2d3c4b5a6
Revises: t8u9v0w1x2y3
Create Date: 2026-03-28 15:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, Sequence[str], None] = "t8u9v0w1x2y3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NOW_SQL = "now()"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("bling_flow_events"):
        op.create_table(
            "bling_flow_events",
            sa.Column("source", sa.String(length=30), nullable=False, server_default="runtime"),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("entity_type", sa.String(length=30), nullable=False, server_default="pedido"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="ok"),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="info"),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("pedido_integrado_id", sa.Integer(), nullable=True),
            sa.Column("pedido_bling_id", sa.String(length=50), nullable=True),
            sa.Column("nf_bling_id", sa.String(length=50), nullable=True),
            sa.Column("sku", sa.String(length=100), nullable=True),
            sa.Column("auto_fix_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("processed_at", sa.DateTime(), nullable=False),
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text(NOW_SQL), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text(NOW_SQL), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not inspector.has_table("bling_flow_incidents"):
        op.create_table(
            "bling_flow_incidents",
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
            sa.Column("source", sa.String(length=30), nullable=False, server_default="auditoria"),
            sa.Column("scope", sa.String(length=30), nullable=False, server_default="pedido"),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("suggested_action", sa.String(length=255), nullable=True),
            sa.Column("auto_fixable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("auto_fix_status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("dedupe_key", sa.String(length=255), nullable=False),
            sa.Column("pedido_integrado_id", sa.Integer(), nullable=True),
            sa.Column("pedido_bling_id", sa.String(length=50), nullable=True),
            sa.Column("nf_bling_id", sa.String(length=50), nullable=True),
            sa.Column("sku", sa.String(length=100), nullable=True),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("first_seen_em", sa.DateTime(), nullable=False),
            sa.Column("last_seen_em", sa.DateTime(), nullable=False),
            sa.Column("resolved_em", sa.DateTime(), nullable=True),
            sa.Column("occurrences", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text(NOW_SQL), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text(NOW_SQL), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_events_tenant_id ON bling_flow_events (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_events_pedido_integrado_id ON bling_flow_events (pedido_integrado_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_events_tenant_created_at ON bling_flow_events (tenant_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_events_pedido_bling_id ON bling_flow_events (pedido_bling_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_events_nf_bling_id ON bling_flow_events (nf_bling_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_events_event_type ON bling_flow_events (event_type)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_incidents_tenant_id ON bling_flow_incidents (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_incidents_pedido_integrado_id ON bling_flow_incidents (pedido_integrado_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_incidents_tenant_status ON bling_flow_incidents (tenant_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_incidents_code ON bling_flow_incidents (code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_incidents_dedupe_key ON bling_flow_incidents (dedupe_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bling_flow_incidents_pedido_bling_id ON bling_flow_incidents (pedido_bling_id)")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("bling_flow_incidents"):
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_incidents_pedido_bling_id")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_incidents_dedupe_key")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_incidents_code")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_incidents_tenant_status")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_incidents_pedido_integrado_id")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_incidents_tenant_id")
        op.drop_table("bling_flow_incidents")

    if inspector.has_table("bling_flow_events"):
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_events_event_type")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_events_nf_bling_id")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_events_pedido_bling_id")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_events_tenant_created_at")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_events_pedido_integrado_id")
        op.execute("DROP INDEX IF EXISTS ix_bling_flow_events_tenant_id")
        op.drop_table("bling_flow_events")
