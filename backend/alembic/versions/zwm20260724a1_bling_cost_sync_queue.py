"""add persistent Bling product cost sync queue

Revision ID: zwm20260724a1
Revises: zwl20260723a1
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zwm20260724a1"
down_revision = "zwl20260723a1"
branch_labels = None
depends_on = None

TABLE_NAME = "produto_bling_cost_sync_queue"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column(
                "id",
                sa.Integer(),
                sa.Identity(always=True),
                nullable=False,
            ),
            sa.Column("produto_id", sa.Integer(), nullable=False),
            sa.Column("preco_custo_novo", sa.Float(), nullable=False),
            sa.Column(
                "bling_produto_fornecedor_id",
                sa.String(length=50),
                nullable=True,
            ),
            sa.Column("motivo", sa.String(length=80), nullable=True),
            sa.Column("origem", sa.String(length=30), nullable=True),
            sa.Column(
                "status",
                sa.String(length=20),
                server_default="pendente",
                nullable=False,
            ),
            sa.Column(
                "forcar_sync",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
            sa.Column(
                "versao",
                sa.Integer(),
                server_default="1",
                nullable=False,
            ),
            sa.Column(
                "tentativas",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
            sa.Column("ultima_tentativa_em", sa.DateTime(), nullable=True),
            sa.Column("proxima_tentativa_em", sa.DateTime(), nullable=True),
            sa.Column("processado_em", sa.DateTime(), nullable=True),
            sa.Column("ultimo_custo_enviado", sa.Float(), nullable=True),
            sa.Column("ultimo_erro", sa.Text(), nullable=True),
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
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["produto_id"],
                ["produtos.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "tenant_id",
                "produto_id",
                name="uq_produto_bling_cost_sync_tenant_produto",
            ),
        )
        op.create_index(
            "ix_produto_bling_cost_sync_queue_produto_id",
            TABLE_NAME,
            ["produto_id"],
            unique=False,
        )
        op.create_index(
            "ix_produto_bling_cost_sync_queue_tenant_id",
            TABLE_NAME,
            ["tenant_id"],
            unique=False,
        )
        op.create_index(
            "ix_produto_bling_cost_sync_ready",
            TABLE_NAME,
            ["tenant_id", "status", "proxima_tentativa_em"],
            unique=False,
        )

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(TABLE_NAME,),
        enable=True,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(TABLE_NAME):
        return

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(TABLE_NAME,),
        enable=False,
    )
    op.drop_index("ix_produto_bling_cost_sync_ready", table_name=TABLE_NAME)
    op.drop_index(
        "ix_produto_bling_cost_sync_queue_tenant_id",
        table_name=TABLE_NAME,
    )
    op.drop_index(
        "ix_produto_bling_cost_sync_queue_produto_id",
        table_name=TABLE_NAME,
    )
    op.drop_table(TABLE_NAME)
