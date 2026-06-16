"""create estoque validade bloqueios

Revision ID: ox20260521a1
Revises: ow20260518a1
Create Date: 2026-05-21 07:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "ox20260521a1"
down_revision: Union[str, Sequence[str], None] = "ow20260518a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _columns(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _indexes(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _create_index_once(name: str, table_name: str, columns: list[str]) -> None:
    if name not in _indexes(table_name):
        op.create_index(name, table_name, columns)


def upgrade() -> None:
    _add_column_once(
        "tenants",
        sa.Column(
            "protecao_validade_ativa",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    _add_column_once(
        "tenants",
        sa.Column(
            "dias_alerta_validade", sa.Integer(), nullable=False, server_default="15"
        ),
    )
    _add_column_once(
        "tenants",
        sa.Column(
            "bloquear_validade_pdv",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    _add_column_once(
        "tenants",
        sa.Column(
            "bloquear_validade_ecommerce",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    _add_column_once(
        "tenants",
        sa.Column(
            "bloquear_validade_integracoes_online",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    if not _has_table("estoque_validade_bloqueios"):
        op.create_table(
            "estoque_validade_bloqueios",
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
            sa.Column(
                "produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False
            ),
            sa.Column(
                "lote_id",
                sa.Integer(),
                sa.ForeignKey("produto_lotes.id"),
                nullable=False,
            ),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
            ),
            sa.Column(
                "status", sa.String(30), nullable=False, server_default="pendente"
            ),
            sa.Column("origem", sa.String(30), nullable=False, server_default="rotina"),
            sa.Column("data_referencia", sa.DateTime(timezone=True), nullable=False),
            sa.Column("data_validade", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "quantidade_bloqueada", sa.Float(), nullable=False, server_default="0"
            ),
            sa.Column(
                "quantidade_resolvida", sa.Float(), nullable=False, server_default="0"
            ),
            sa.Column("custo_unitario", sa.Float(), nullable=True),
            sa.Column(
                "custo_total_estimado", sa.Float(), nullable=False, server_default="0"
            ),
            sa.Column(
                "movimentacao_bloqueio_id",
                sa.Integer(),
                sa.ForeignKey("estoque_movimentacoes.id"),
                nullable=True,
            ),
            sa.Column(
                "movimentacao_resolucao_id",
                sa.Integer(),
                sa.ForeignKey("estoque_movimentacoes.id"),
                nullable=True,
            ),
            sa.Column(
                "decidido_por_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("decidido_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decisao", sa.String(30), nullable=True),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_once(
        "ix_estoque_validade_tenant_status",
        "estoque_validade_bloqueios",
        ["tenant_id", "status"],
    )
    _create_index_once(
        "ix_estoque_validade_tenant_produto",
        "estoque_validade_bloqueios",
        ["tenant_id", "produto_id"],
    )
    _create_index_once(
        "ix_estoque_validade_tenant_lote",
        "estoque_validade_bloqueios",
        ["tenant_id", "lote_id"],
    )
    _create_index_once(
        "ix_estoque_validade_lote_status",
        "estoque_validade_bloqueios",
        ["lote_id", "status"],
    )


def downgrade() -> None:
    if _has_table("estoque_validade_bloqueios"):
        op.drop_table("estoque_validade_bloqueios")
