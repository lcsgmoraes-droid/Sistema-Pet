"""add comissoes itens provisao columns

Revision ID: pa20260526a1
Revises: oz20260525a1
Create Date: 2026-05-26 11:25:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "pa20260526a1"
down_revision: Union[str, Sequence[str], None] = "oz20260525a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")}


def upgrade() -> None:
    existing_columns = _columns("comissoes_itens")

    if "comissao_provisionada" not in existing_columns:
        op.add_column(
            "comissoes_itens",
            sa.Column("comissao_provisionada", sa.Boolean(), nullable=True, server_default=sa.false()),
        )

    if "conta_pagar_id" not in existing_columns:
        op.add_column(
            "comissoes_itens",
            sa.Column("conta_pagar_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_comissoes_itens_conta_pagar_id",
            "comissoes_itens",
            "contas_pagar",
            ["conta_pagar_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if "data_provisao" not in existing_columns:
        op.add_column(
            "comissoes_itens",
            sa.Column("data_provisao", sa.Date(), nullable=True),
        )

    existing_indexes = _indexes("comissoes_itens")
    if "ix_comissoes_itens_comissao_provisionada" not in existing_indexes:
        op.create_index(
            "ix_comissoes_itens_comissao_provisionada",
            "comissoes_itens",
            ["comissao_provisionada"],
            unique=False,
            postgresql_where=sa.text("comissao_provisionada = false"),
        )

    if "ix_comissoes_itens_conta_pagar_id" not in existing_indexes:
        op.create_index(
            "ix_comissoes_itens_conta_pagar_id",
            "comissoes_itens",
            ["conta_pagar_id"],
            unique=False,
        )


def downgrade() -> None:
    existing_indexes = _indexes("comissoes_itens")
    if "ix_comissoes_itens_conta_pagar_id" in existing_indexes:
        op.drop_index("ix_comissoes_itens_conta_pagar_id", table_name="comissoes_itens")
    if "ix_comissoes_itens_comissao_provisionada" in existing_indexes:
        op.drop_index("ix_comissoes_itens_comissao_provisionada", table_name="comissoes_itens")

    existing_columns = _columns("comissoes_itens")
    existing_fks = _foreign_keys("comissoes_itens")
    if "conta_pagar_id" in existing_columns:
        if "fk_comissoes_itens_conta_pagar_id" in existing_fks:
            op.drop_constraint("fk_comissoes_itens_conta_pagar_id", "comissoes_itens", type_="foreignkey")
        op.drop_column("comissoes_itens", "conta_pagar_id")
    if "data_provisao" in existing_columns:
        op.drop_column("comissoes_itens", "data_provisao")
    if "comissao_provisionada" in existing_columns:
        op.drop_column("comissoes_itens", "comissao_provisionada")
