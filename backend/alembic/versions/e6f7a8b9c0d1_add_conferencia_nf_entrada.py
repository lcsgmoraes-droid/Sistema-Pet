"""add conferencia fields to notas de entrada

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table_name)} if inspector.has_table(table_name) else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    nota_columns = _column_names(inspector, "notas_entrada")
    item_columns = _column_names(inspector, "notas_entrada_itens")

    if "conferencia_status" not in nota_columns:
        op.add_column(
            "notas_entrada",
            sa.Column("conferencia_status", sa.String(length=30), nullable=True, server_default="nao_iniciada"),
        )
    if "conferencia_observacoes" not in nota_columns:
        op.add_column("notas_entrada", sa.Column("conferencia_observacoes", sa.Text(), nullable=True))
    if "conferencia_realizada_em" not in nota_columns:
        op.add_column("notas_entrada", sa.Column("conferencia_realizada_em", sa.DateTime(), nullable=True))
    if "conferencia_user_id" not in nota_columns:
        op.add_column("notas_entrada", sa.Column("conferencia_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_notas_entrada_conferencia_user_id_users",
            "notas_entrada",
            "users",
            ["conferencia_user_id"],
            ["id"],
        )

    if "quantidade_conferida" not in item_columns:
        op.add_column("notas_entrada_itens", sa.Column("quantidade_conferida", sa.Float(), nullable=True))
    if "quantidade_avariada" not in item_columns:
        op.add_column(
            "notas_entrada_itens",
            sa.Column("quantidade_avariada", sa.Float(), nullable=True, server_default="0"),
        )
    if "observacao_conferencia" not in item_columns:
        op.add_column("notas_entrada_itens", sa.Column("observacao_conferencia", sa.Text(), nullable=True))
    if "acao_sugerida" not in item_columns:
        op.add_column(
            "notas_entrada_itens",
            sa.Column("acao_sugerida", sa.String(length=40), nullable=True, server_default="sem_acao"),
        )

    nota_indexes = _index_names(inspector, "notas_entrada")
    if "ix_notas_entrada_conferencia_status" not in nota_indexes:
        op.create_index("ix_notas_entrada_conferencia_status", "notas_entrada", ["conferencia_status"])
    if "ix_notas_entrada_conferencia_user_id" not in nota_indexes:
        op.create_index("ix_notas_entrada_conferencia_user_id", "notas_entrada", ["conferencia_user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    nota_indexes = _index_names(inspector, "notas_entrada")
    if "ix_notas_entrada_conferencia_user_id" in nota_indexes:
        op.drop_index("ix_notas_entrada_conferencia_user_id", table_name="notas_entrada")
    if "ix_notas_entrada_conferencia_status" in nota_indexes:
        op.drop_index("ix_notas_entrada_conferencia_status", table_name="notas_entrada")

    nota_columns = _column_names(inspector, "notas_entrada")
    if "conferencia_user_id" in nota_columns:
        op.drop_constraint("fk_notas_entrada_conferencia_user_id_users", "notas_entrada", type_="foreignkey")
        op.drop_column("notas_entrada", "conferencia_user_id")
    if "conferencia_realizada_em" in nota_columns:
        op.drop_column("notas_entrada", "conferencia_realizada_em")
    if "conferencia_observacoes" in nota_columns:
        op.drop_column("notas_entrada", "conferencia_observacoes")
    if "conferencia_status" in nota_columns:
        op.drop_column("notas_entrada", "conferencia_status")

    item_columns = _column_names(inspector, "notas_entrada_itens")
    if "acao_sugerida" in item_columns:
        op.drop_column("notas_entrada_itens", "acao_sugerida")
    if "observacao_conferencia" in item_columns:
        op.drop_column("notas_entrada_itens", "observacao_conferencia")
    if "quantidade_avariada" in item_columns:
        op.drop_column("notas_entrada_itens", "quantidade_avariada")
    if "quantidade_conferida" in item_columns:
        op.drop_column("notas_entrada_itens", "quantidade_conferida")
