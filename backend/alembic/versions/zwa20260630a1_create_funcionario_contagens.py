"""create funcionario contagens

Revision ID: zwa20260630a1
Revises: uv20260630a1
Create Date: 2026-06-30 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "zwa20260630a1"
down_revision: Union[str, Sequence[str], None] = "uv20260630a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _indexes(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _create_index(name: str, table_name: str, columns: list[str]) -> None:
    if name not in _indexes(table_name):
        op.create_index(name, table_name, columns)


def _tenant_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
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


def upgrade() -> None:
    if not _has_table("funcionario_contagens"):
        op.create_table(
            "funcionario_contagens",
            *_tenant_columns(),
            sa.Column("funcionario_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("fornecedor_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
            sa.Column("fornecedor_nome_snapshot", sa.String(length=255), nullable=True),
            sa.Column("titulo", sa.String(length=160), nullable=False, server_default="Contagem"),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="salva"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("funcionario_contagem_itens"):
        op.create_table(
            "funcionario_contagem_itens",
            *_tenant_columns(),
            sa.Column(
                "contagem_id",
                sa.Integer(),
                sa.ForeignKey("funcionario_contagens.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("codigo", sa.String(length=50), nullable=True),
            sa.Column("codigo_barras", sa.String(length=50), nullable=True),
            sa.Column("gtin_ean", sa.String(length=50), nullable=True),
            sa.Column("nome", sa.String(length=255), nullable=False),
            sa.Column("unidade", sa.String(length=20), nullable=False, server_default="UN"),
            sa.Column("quantidade", sa.Float(), nullable=False, server_default="0"),
            sa.Column("preco_custo_snapshot", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("preco_venda_snapshot", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index("ix_funcionario_contagens_tenant_created", "funcionario_contagens", ["tenant_id", "created_at"])
    _create_index("ix_funcionario_contagens_tenant_funcionario", "funcionario_contagens", ["tenant_id", "funcionario_id"])
    _create_index("ix_funcionario_contagens_tenant_fornecedor", "funcionario_contagens", ["tenant_id", "fornecedor_id"])
    _create_index("ix_funcionario_contagem_itens_tenant_contagem", "funcionario_contagem_itens", ["tenant_id", "contagem_id"])
    _create_index("ix_funcionario_contagem_itens_tenant_produto", "funcionario_contagem_itens", ["tenant_id", "produto_id"])


def downgrade() -> None:
    if _has_table("funcionario_contagem_itens"):
        op.drop_table("funcionario_contagem_itens")
    if _has_table("funcionario_contagens"):
        op.drop_table("funcionario_contagens")
