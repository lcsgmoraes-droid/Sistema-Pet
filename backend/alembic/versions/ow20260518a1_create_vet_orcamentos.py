"""create vet orcamentos

Revision ID: ow20260518a1
Revises: ov20260517a2
Create Date: 2026-05-18 21:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "ow20260518a1"
down_revision: Union[str, Sequence[str], None] = "ov20260517a2"
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    if not _has_table("vet_orcamentos"):
        op.create_table(
            "vet_orcamentos",
            *_tenant_columns(),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("vet_consultas.id"), nullable=True),
            sa.Column("internacao_id", sa.Integer(), sa.ForeignKey("vet_internacoes.id"), nullable=True),
            sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=True),
            sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
            sa.Column("veterinario_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
            sa.Column("titulo", sa.String(255), nullable=False, server_default="Orcamento veterinario"),
            sa.Column("status", sa.String(30), nullable=False, server_default="rascunho"),
            sa.Column("previsao_dias_internacao", sa.Integer(), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("custo_total_estimado", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("preco_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("margem_valor", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("margem_percentual", sa.Float(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("vet_orcamento_itens"):
        op.create_table(
            "vet_orcamento_itens",
            *_tenant_columns(),
            sa.Column("orcamento_id", sa.Integer(), sa.ForeignKey("vet_orcamentos.id"), nullable=False),
            sa.Column("catalogo_id", sa.Integer(), sa.ForeignKey("vet_catalogo_procedimentos.id"), nullable=True),
            sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=True),
            sa.Column("origem", sa.String(30), nullable=False, server_default="manual"),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("nome", sa.String(255), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("unidade", sa.String(50), nullable=True),
            sa.Column("quantidade", sa.Float(), nullable=False, server_default="1"),
            sa.Column("custo_unitario_estimado", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("preco_unitario_sugerido", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("preco_unitario", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("custo_total_estimado", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("preco_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("margem_valor", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("margem_percentual", sa.Float(), nullable=False, server_default="0"),
            sa.Column("insumos", sa.JSON(), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index("ix_vet_orcamentos_tenant_id", "vet_orcamentos", ["tenant_id"])
    _create_index("ix_vet_orcamentos_user_id", "vet_orcamentos", ["user_id"])
    _create_index("ix_vet_orcamentos_consulta_id", "vet_orcamentos", ["consulta_id"])
    _create_index("ix_vet_orcamentos_internacao_id", "vet_orcamentos", ["internacao_id"])
    _create_index("ix_vet_orcamentos_pet_id", "vet_orcamentos", ["pet_id"])
    _create_index("ix_vet_orcamentos_cliente_id", "vet_orcamentos", ["cliente_id"])
    _create_index("ix_vet_orcamentos_veterinario_id", "vet_orcamentos", ["veterinario_id"])
    _create_index("ix_vet_orcamentos_status", "vet_orcamentos", ["status"])
    _create_index("ix_vet_orcamentos_tenant_status", "vet_orcamentos", ["tenant_id", "status"])
    _create_index("ix_vet_orcamentos_tenant_consulta", "vet_orcamentos", ["tenant_id", "consulta_id"])
    _create_index("ix_vet_orcamentos_tenant_internacao", "vet_orcamentos", ["tenant_id", "internacao_id"])

    _create_index("ix_vet_orcamento_itens_tenant_id", "vet_orcamento_itens", ["tenant_id"])
    _create_index("ix_vet_orcamento_itens_orcamento_id", "vet_orcamento_itens", ["orcamento_id"])
    _create_index("ix_vet_orcamento_itens_catalogo_id", "vet_orcamento_itens", ["catalogo_id"])
    _create_index("ix_vet_orcamento_itens_produto_id", "vet_orcamento_itens", ["produto_id"])
    _create_index(
        "ix_vet_orcamento_itens_tenant_orcamento",
        "vet_orcamento_itens",
        ["tenant_id", "orcamento_id"],
    )


def downgrade() -> None:
    if _has_table("vet_orcamento_itens"):
        op.drop_table("vet_orcamento_itens")
    if _has_table("vet_orcamentos"):
        op.drop_table("vet_orcamentos")
