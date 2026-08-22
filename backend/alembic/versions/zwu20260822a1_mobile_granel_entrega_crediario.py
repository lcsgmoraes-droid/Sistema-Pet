"""mobile granel configuration and delivery ratings

Revision ID: zwu20260822a1
Revises: zws20260821a1
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zwu20260822a1"
down_revision = "zws20260821a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "tenants" in tables:
        tenant_columns = {column["name"] for column in inspector.get_columns("tenants")}
        if "granel_bipagem_obrigatoria" not in tenant_columns:
            op.add_column(
                "tenants",
                sa.Column(
                    "granel_bipagem_obrigatoria",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                ),
            )

    if "entrega_avaliacoes" not in tables:
        op.create_table(
            "entrega_avaliacoes",
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("venda_id", sa.Integer(), nullable=False),
            sa.Column("cliente_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("nota", sa.Integer(), nullable=False),
            sa.Column("comentario", sa.Text(), nullable=True),
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
            sa.CheckConstraint(
                "nota >= 1 AND nota <= 5", name="ck_entrega_avaliacao_nota"
            ),
            sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["venda_id"], ["vendas.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "tenant_id", "venda_id", name="uq_entrega_avaliacao_venda"
            ),
        )
        op.create_index(
            "ix_entrega_avaliacoes_tenant_id", "entrega_avaliacoes", ["tenant_id"]
        )
        op.create_index(
            "ix_entrega_avaliacoes_venda_id", "entrega_avaliacoes", ["venda_id"]
        )
        op.create_index(
            "ix_entrega_avaliacoes_cliente_id", "entrega_avaliacoes", ["cliente_id"]
        )
        op.create_index(
            "ix_entrega_avaliacoes_user_id", "entrega_avaliacoes", ["user_id"]
        )

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=("entrega_avaliacoes",),
        enable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "entrega_avaliacoes" in tables:
        apply_tenant_rls(
            op_module=op,
            sa_module=sa,
            table_names=("entrega_avaliacoes",),
            enable=False,
        )
        op.drop_table("entrega_avaliacoes")
    if "tenants" in tables:
        tenant_columns = {
            column["name"] for column in sa.inspect(bind).get_columns("tenants")
        }
        if "granel_bipagem_obrigatoria" in tenant_columns:
            op.drop_column("tenants", "granel_bipagem_obrigatoria")
