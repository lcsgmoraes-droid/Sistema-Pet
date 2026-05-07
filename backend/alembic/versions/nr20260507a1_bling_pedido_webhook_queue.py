"""create bling order webhook queue

Revision ID: nr20260507a1
Revises: nq20260504a1
Create Date: 2026-05-07 13:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "nr20260507a1"
down_revision = "nq20260504a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bling_pedido_webhook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=96), nullable=False),
        sa.Column("event_id", sa.String(length=120), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("pedido_bling_id", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index(op.f("ix_bling_pedido_webhook_events_id"), "bling_pedido_webhook_events", ["id"], unique=False)
    op.create_index(op.f("ix_bling_pedido_webhook_events_tenant_id"), "bling_pedido_webhook_events", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_bling_pedido_webhook_events_dedupe_key"), "bling_pedido_webhook_events", ["dedupe_key"], unique=False)
    op.create_index(op.f("ix_bling_pedido_webhook_events_event_id"), "bling_pedido_webhook_events", ["event_id"], unique=False)
    op.create_index(op.f("ix_bling_pedido_webhook_events_event_type"), "bling_pedido_webhook_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_bling_pedido_webhook_events_pedido_bling_id"), "bling_pedido_webhook_events", ["pedido_bling_id"], unique=False)
    op.create_index(op.f("ix_bling_pedido_webhook_events_status"), "bling_pedido_webhook_events", ["status"], unique=False)
    op.create_index(op.f("ix_bling_pedido_webhook_events_next_attempt_at"), "bling_pedido_webhook_events", ["next_attempt_at"], unique=False)
    op.create_index("ix_bling_pedido_webhook_status_next", "bling_pedido_webhook_events", ["status", "next_attempt_at"], unique=False)
    op.create_index("ix_bling_pedido_webhook_tenant_status", "bling_pedido_webhook_events", ["tenant_id", "status"], unique=False)
    op.create_index("ix_bling_pedido_webhook_pedido_status", "bling_pedido_webhook_events", ["pedido_bling_id", "status"], unique=False)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_tenant_bling_id "
        "ON pedidos_integrados (tenant_id, pedido_bling_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_tenant_bling_numero "
        "ON pedidos_integrados (tenant_id, pedido_bling_numero)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_tenant_status_created "
        "ON pedidos_integrados (tenant_id, status, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_itens_tenant_pedido "
        "ON pedidos_integrados_itens (tenant_id, pedido_integrado_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_itens_tenant_sku_active "
        "ON pedidos_integrados_itens (tenant_id, sku) "
        "WHERE liberado_em IS NULL AND vendido_em IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pedidos_integrados_itens_tenant_sku_active")
    op.execute("DROP INDEX IF EXISTS ix_pedidos_integrados_itens_tenant_pedido")
    op.execute("DROP INDEX IF EXISTS ix_pedidos_integrados_tenant_status_created")
    op.execute("DROP INDEX IF EXISTS ix_pedidos_integrados_tenant_bling_numero")
    op.execute("DROP INDEX IF EXISTS ix_pedidos_integrados_tenant_bling_id")

    op.drop_index("ix_bling_pedido_webhook_pedido_status", table_name="bling_pedido_webhook_events")
    op.drop_index("ix_bling_pedido_webhook_tenant_status", table_name="bling_pedido_webhook_events")
    op.drop_index("ix_bling_pedido_webhook_status_next", table_name="bling_pedido_webhook_events")
    op.drop_index(op.f("ix_bling_pedido_webhook_events_next_attempt_at"), table_name="bling_pedido_webhook_events")
    op.drop_index(op.f("ix_bling_pedido_webhook_events_status"), table_name="bling_pedido_webhook_events")
    op.drop_index(op.f("ix_bling_pedido_webhook_events_pedido_bling_id"), table_name="bling_pedido_webhook_events")
    op.drop_index(op.f("ix_bling_pedido_webhook_events_event_type"), table_name="bling_pedido_webhook_events")
    op.drop_index(op.f("ix_bling_pedido_webhook_events_event_id"), table_name="bling_pedido_webhook_events")
    op.drop_index(op.f("ix_bling_pedido_webhook_events_dedupe_key"), table_name="bling_pedido_webhook_events")
    op.drop_index(op.f("ix_bling_pedido_webhook_events_tenant_id"), table_name="bling_pedido_webhook_events")
    op.drop_index(op.f("ix_bling_pedido_webhook_events_id"), table_name="bling_pedido_webhook_events")
    op.drop_table("bling_pedido_webhook_events")
