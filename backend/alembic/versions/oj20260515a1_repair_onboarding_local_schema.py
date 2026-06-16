"""repair onboarding local schema gaps

Revision ID: oj20260515a1
Revises: oi20260513a1
Create Date: 2026-05-15 15:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "oj20260515a1"
down_revision = "oi20260513a1"
branch_labels = None
depends_on = None


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("categorias_financeiras"):
        columns = {
            column["name"] for column in inspector.get_columns("categorias_financeiras")
        }
        if "tipo_custo" not in columns:
            op.add_column(
                "categorias_financeiras",
                sa.Column("tipo_custo", sa.String(length=20), nullable=True),
            )

    if not inspector.has_table("bling_pedido_webhook_events"):
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
            sa.Column(
                "next_attempt_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("response_payload", sa.JSON(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("dedupe_key"),
        )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "bling_pedido_webhook_events")
    webhook_indexes = {
        "ix_bling_pedido_webhook_events_id": ["id"],
        "ix_bling_pedido_webhook_events_tenant_id": ["tenant_id"],
        "ix_bling_pedido_webhook_events_dedupe_key": ["dedupe_key"],
        "ix_bling_pedido_webhook_events_event_id": ["event_id"],
        "ix_bling_pedido_webhook_events_event_type": ["event_type"],
        "ix_bling_pedido_webhook_events_pedido_bling_id": ["pedido_bling_id"],
        "ix_bling_pedido_webhook_events_status": ["status"],
        "ix_bling_pedido_webhook_events_next_attempt_at": ["next_attempt_at"],
        "ix_bling_pedido_webhook_status_next": ["status", "next_attempt_at"],
        "ix_bling_pedido_webhook_tenant_status": ["tenant_id", "status"],
        "ix_bling_pedido_webhook_pedido_status": ["pedido_bling_id", "status"],
    }
    for index_name, columns in webhook_indexes.items():
        if index_name not in indexes:
            op.create_index(
                index_name, "bling_pedido_webhook_events", columns, unique=False
            )

    if inspector.has_table("pedidos_integrados"):
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

    if inspector.has_table("pedidos_integrados_itens"):
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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("categorias_financeiras"):
        columns = {
            column["name"] for column in inspector.get_columns("categorias_financeiras")
        }
        if "tipo_custo" in columns:
            op.drop_column("categorias_financeiras", "tipo_custo")

    if inspector.has_table("bling_pedido_webhook_events"):
        op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_pedido_status")
        op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_tenant_status")
        op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_status_next")
        op.execute(
            "DROP INDEX IF EXISTS ix_bling_pedido_webhook_events_next_attempt_at"
        )
        op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_events_status")
        op.execute(
            "DROP INDEX IF EXISTS ix_bling_pedido_webhook_events_pedido_bling_id"
        )
        op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_events_event_type")
        op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_events_event_id")
        op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_events_dedupe_key")
        op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_events_tenant_id")
        op.execute("DROP INDEX IF EXISTS ix_bling_pedido_webhook_events_id")
        op.drop_table("bling_pedido_webhook_events")
