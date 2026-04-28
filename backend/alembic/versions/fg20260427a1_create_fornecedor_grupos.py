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
    op.create_index("ix_fornecedor_grupos_tenant_id", "fornecedor_grupos", ["tenant_id"])
    op.create_index("ix_fornecedor_grupos_nome", "fornecedor_grupos", ["nome"])
    op.create_index("ix_fornecedor_grupos_fornecedor_principal_id", "fornecedor_grupos", ["fornecedor_principal_id"])
    op.create_index("ix_fornecedor_grupos_tenant_ativo", "fornecedor_grupos", ["tenant_id", "ativo"])

    op.add_column("clientes", sa.Column("fornecedor_grupo_id", sa.Integer(), nullable=True))
    op.create_index("ix_clientes_fornecedor_grupo_id", "clientes", ["fornecedor_grupo_id"])
    op.create_foreign_key(
        "fk_clientes_fornecedor_grupo_id",
        "clientes",
        "fornecedor_grupos",
        ["fornecedor_grupo_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_clientes_fornecedor_grupo_id", "clientes", type_="foreignkey")
    op.drop_index("ix_clientes_fornecedor_grupo_id", table_name="clientes")
    op.drop_column("clientes", "fornecedor_grupo_id")

    op.drop_index("ix_fornecedor_grupos_tenant_ativo", table_name="fornecedor_grupos")
    op.drop_index("ix_fornecedor_grupos_fornecedor_principal_id", table_name="fornecedor_grupos")
    op.drop_index("ix_fornecedor_grupos_nome", table_name="fornecedor_grupos")
    op.drop_index("ix_fornecedor_grupos_tenant_id", table_name="fornecedor_grupos")
    op.drop_table("fornecedor_grupos")
