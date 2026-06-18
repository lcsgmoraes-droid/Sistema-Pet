"""create missing ecommerce order tables

Revision ID: oq20260515a8
Revises: op20260515a7
Create Date: 2026-05-15 18:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "oq20260515a8"
down_revision = "op20260515a7"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _columns(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    if index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade() -> None:
    inspector = _inspector()

    if not inspector.has_table("pedidos"):
        op.create_table(
            "pedidos",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("pedido_id", sa.String(), nullable=True),
            sa.Column("cliente_id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("total", sa.Float(), nullable=False),
            sa.Column("origem", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=True, server_default="criado"),
            sa.Column("tipo_retirada", sa.String(length=20), nullable=True),
            sa.Column("palavra_chave_retirada", sa.String(length=100), nullable=True),
            sa.Column("is_drive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("drive_chegou_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("drive_entregue_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("pedido_id", name="uq_pedidos_pedido_id"),
        )
    else:
        columns = _columns("pedidos")
        if "is_drive" not in columns:
            op.add_column("pedidos", sa.Column("is_drive", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        if "drive_chegou_at" not in columns:
            op.add_column("pedidos", sa.Column("drive_chegou_at", sa.DateTime(timezone=True), nullable=True))
        if "drive_entregue_at" not in columns:
            op.add_column("pedidos", sa.Column("drive_entregue_at", sa.DateTime(timezone=True), nullable=True))

    _create_index_if_missing("ix_pedidos_id", "pedidos", ["id"])
    _create_index_if_missing("ix_pedidos_pedido_id", "pedidos", ["pedido_id"], unique=True)
    _create_index_if_missing("ix_pedidos_tenant_id", "pedidos", ["tenant_id"])

    inspector = _inspector()
    if not inspector.has_table("pedido_itens"):
        op.create_table(
            "pedido_itens",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("pedido_id", sa.String(), nullable=False),
            sa.Column("produto_id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(), nullable=False),
            sa.Column("quantidade", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("preco_unitario", sa.Float(), nullable=False),
            sa.Column("subtotal", sa.Float(), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.pedido_id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing("ix_pedido_itens_id", "pedido_itens", ["id"])
    _create_index_if_missing("ix_pedido_itens_pedido_id", "pedido_itens", ["pedido_id"])
    _create_index_if_missing("ix_pedido_itens_tenant_id", "pedido_itens", ["tenant_id"])


def downgrade() -> None:
    # Repair migration: keep downgrade non-destructive so an accidental rollback
    # does not remove operational e-commerce orders from environments that
    # already had these tables before this revision.
    return
