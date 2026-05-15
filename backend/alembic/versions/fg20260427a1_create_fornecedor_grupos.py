"""create fornecedor grupos

Revision ID: fg20260427a1
Revises: d4e5f6a7b9c0
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "fg20260427a1"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("fornecedor_grupos"):
        op.create_table(
            "fornecedor_grupos",
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("nome", sa.String(length=255), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("fornecedor_principal_id", sa.Integer(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "nome", name="uq_fornecedor_grupos_tenant_nome"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_fornecedor_grupos_tenant_id ON fornecedor_grupos (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fornecedor_grupos_nome ON fornecedor_grupos (nome)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fornecedor_grupos_fornecedor_principal_id "
        "ON fornecedor_grupos (fornecedor_principal_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_fornecedor_grupos_tenant_ativo ON fornecedor_grupos (tenant_id, ativo)")

    inspector = sa.inspect(bind)
    if inspector.has_table("clientes"):
        cliente_columns = {column["name"] for column in inspector.get_columns("clientes")}
        cliente_indexes = {index["name"] for index in inspector.get_indexes("clientes")}
        cliente_fks = {fk["name"] for fk in inspector.get_foreign_keys("clientes")}

        if "fornecedor_grupo_id" not in cliente_columns:
            op.add_column("clientes", sa.Column("fornecedor_grupo_id", sa.Integer(), nullable=True))
        if "ix_clientes_fornecedor_grupo_id" not in cliente_indexes:
            op.create_index("ix_clientes_fornecedor_grupo_id", "clientes", ["fornecedor_grupo_id"])
        if "fk_clientes_fornecedor_grupo_id" not in cliente_fks:
            op.create_foreign_key(
                "fk_clientes_fornecedor_grupo_id",
                "clientes",
                "fornecedor_grupos",
                ["fornecedor_grupo_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("clientes"):
        cliente_columns = {column["name"] for column in inspector.get_columns("clientes")}
        cliente_indexes = {index["name"] for index in inspector.get_indexes("clientes")}
        cliente_fks = {fk["name"] for fk in inspector.get_foreign_keys("clientes")}

        if "fk_clientes_fornecedor_grupo_id" in cliente_fks:
            op.drop_constraint("fk_clientes_fornecedor_grupo_id", "clientes", type_="foreignkey")
        if "ix_clientes_fornecedor_grupo_id" in cliente_indexes:
            op.drop_index("ix_clientes_fornecedor_grupo_id", table_name="clientes")
        if "fornecedor_grupo_id" in cliente_columns:
            op.drop_column("clientes", "fornecedor_grupo_id")

    if inspector.has_table("fornecedor_grupos"):
        op.execute("DROP INDEX IF EXISTS ix_fornecedor_grupos_tenant_ativo")
        op.execute("DROP INDEX IF EXISTS ix_fornecedor_grupos_fornecedor_principal_id")
        op.execute("DROP INDEX IF EXISTS ix_fornecedor_grupos_nome")
        op.execute("DROP INDEX IF EXISTS ix_fornecedor_grupos_tenant_id")
        op.drop_table("fornecedor_grupos")
