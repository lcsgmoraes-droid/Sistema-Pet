"""ecommerce store configuration and anonymous funnel events

Revision ID: zwn20260729a1
Revises: zwm20260724a1
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zwn20260729a1"
down_revision = "zwm20260724a1"
branch_labels = None
depends_on = None

EVENTS_TABLE = "ecommerce_analytics_events"


def _add_tenant_column(inspector, name, column) -> None:
    existing = {item["name"] for item in inspector.get_columns("tenants")}
    if name not in existing:
        op.add_column("tenants", column)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    _add_tenant_column(
        inspector,
        "ecommerce_entrega_ativa",
        sa.Column(
            "ecommerce_entrega_ativa",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    inspector = sa.inspect(op.get_bind())
    _add_tenant_column(
        inspector,
        "ecommerce_retirada_ativa",
        sa.Column(
            "ecommerce_retirada_ativa",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    inspector = sa.inspect(op.get_bind())
    _add_tenant_column(
        inspector,
        "ecommerce_taxa_entrega",
        sa.Column(
            "ecommerce_taxa_entrega",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
    )
    inspector = sa.inspect(op.get_bind())
    _add_tenant_column(
        inspector,
        "ecommerce_frete_gratis_acima",
        sa.Column("ecommerce_frete_gratis_acima", sa.Float(), nullable=True),
    )
    inspector = sa.inspect(op.get_bind())
    _add_tenant_column(
        inspector,
        "ecommerce_pedido_minimo",
        sa.Column(
            "ecommerce_pedido_minimo",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
    )
    inspector = sa.inspect(op.get_bind())
    _add_tenant_column(
        inspector,
        "ecommerce_prazo_entrega_texto",
        sa.Column("ecommerce_prazo_entrega_texto", sa.String(80), nullable=True),
    )
    inspector = sa.inspect(op.get_bind())
    for name, default in (
        ("ecommerce_usar_estoque_canal", "false"),
        ("ecommerce_ocultar_sem_estoque", "true"),
        ("ecommerce_ocultar_sem_imagem", "false"),
        ("ecommerce_ocultar_servicos", "true"),
    ):
        _add_tenant_column(
            inspector,
            name,
            sa.Column(
                name,
                sa.Boolean(),
                server_default=sa.text(default),
                nullable=False,
            ),
        )
        inspector = sa.inspect(op.get_bind())
    _add_tenant_column(
        inspector,
        "ecommerce_cor_primaria",
        sa.Column(
            "ecommerce_cor_primaria",
            sa.String(7),
            server_default="#f97316",
            nullable=False,
        ),
    )
    inspector = sa.inspect(op.get_bind())
    _add_tenant_column(
        inspector,
        "ecommerce_cor_secundaria",
        sa.Column(
            "ecommerce_cor_secundaria",
            sa.String(7),
            server_default="#0f766e",
            nullable=False,
        ),
    )

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(EVENTS_TABLE):
        op.create_table(
            EVENTS_TABLE,
            sa.Column("event_name", sa.String(40), nullable=False),
            sa.Column("session_id", sa.String(80), nullable=False),
            sa.Column(
                "channel",
                sa.String(20),
                server_default="ecommerce",
                nullable=False,
            ),
            sa.Column("path", sa.String(300), nullable=True),
            sa.Column("product_id", sa.Integer(), nullable=True),
            sa.Column("pedido_id", sa.String(80), nullable=True),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("extra_data", postgresql.JSONB(), nullable=True),
            sa.Column(
                "id",
                sa.Integer(),
                sa.Identity(always=True),
                nullable=False,
            ),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
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
        )
        op.create_index(
            "ix_ecommerce_analytics_events_event_name",
            EVENTS_TABLE,
            ["event_name"],
        )
        op.create_index(
            "ix_ecommerce_analytics_events_tenant_id",
            EVENTS_TABLE,
            ["tenant_id"],
        )
        op.create_index(
            "ix_ecommerce_analytics_tenant_event_created",
            EVENTS_TABLE,
            ["tenant_id", "event_name", "created_at"],
        )
        op.create_index(
            "ix_ecommerce_analytics_tenant_session_created",
            EVENTS_TABLE,
            ["tenant_id", "session_id", "created_at"],
        )
        op.create_index(
            "ix_ecommerce_analytics_tenant_channel_created",
            EVENTS_TABLE,
            ["tenant_id", "channel", "created_at"],
        )

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(EVENTS_TABLE,),
        enable=True,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(EVENTS_TABLE):
        apply_tenant_rls(
            op_module=op,
            sa_module=sa,
            table_names=(EVENTS_TABLE,),
            enable=False,
        )
        op.drop_table(EVENTS_TABLE)

    for name in (
        "ecommerce_cor_secundaria",
        "ecommerce_cor_primaria",
        "ecommerce_ocultar_servicos",
        "ecommerce_ocultar_sem_imagem",
        "ecommerce_ocultar_sem_estoque",
        "ecommerce_usar_estoque_canal",
        "ecommerce_prazo_entrega_texto",
        "ecommerce_pedido_minimo",
        "ecommerce_frete_gratis_acima",
        "ecommerce_taxa_entrega",
        "ecommerce_retirada_ativa",
        "ecommerce_entrega_ativa",
    ):
        inspector = sa.inspect(op.get_bind())
        existing = {item["name"] for item in inspector.get_columns("tenants")}
        if name in existing:
            op.drop_column("tenants", name)
