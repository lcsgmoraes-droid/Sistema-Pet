"""add remuneracao funcionarios

Revision ID: oy20260521a2
Revises: ox20260521a1
Create Date: 2026-05-21 17:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "oy20260521a2"
down_revision: Union[str, Sequence[str], None] = "ox20260521a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _columns(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _drop_column_once(table_name: str, column_name: str) -> None:
    if column_name in _columns(table_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_once("cargos", sa.Column("regime_remuneracao", sa.String(30), nullable=False, server_default="clt"))
    _add_column_once("cargos", sa.Column("gera_encargos", sa.Boolean(), nullable=False, server_default=sa.true()))
    _add_column_once("cargos", sa.Column("inss_funcionario_percentual", sa.Numeric(), nullable=False, server_default="0"))
    _add_column_once("cargos", sa.Column("inss_funcionario_valor", sa.Numeric(), nullable=False, server_default="0"))
    _add_column_once("cargos", sa.Column("desconto_transporte_valor", sa.Numeric(), nullable=False, server_default="0"))
    _add_column_once("cargos", sa.Column("outros_descontos_valor", sa.Numeric(), nullable=False, server_default="0"))

    _add_column_once("clientes", sa.Column("salario_base_override", sa.Numeric(10, 2), nullable=True))
    _add_column_once("clientes", sa.Column("liquido_combinado", sa.Numeric(10, 2), nullable=True))
    _add_column_once("clientes", sa.Column("complemento_modo", sa.String(20), nullable=False, server_default="automatico"))
    _add_column_once("clientes", sa.Column("complemento_fixo_valor", sa.Numeric(10, 2), nullable=False, server_default="0"))
    _add_column_once("clientes", sa.Column("remuneracao_observacoes", sa.Text(), nullable=True))


def downgrade() -> None:
    _drop_column_once("clientes", "remuneracao_observacoes")
    _drop_column_once("clientes", "complemento_fixo_valor")
    _drop_column_once("clientes", "complemento_modo")
    _drop_column_once("clientes", "liquido_combinado")
    _drop_column_once("clientes", "salario_base_override")

    _drop_column_once("cargos", "outros_descontos_valor")
    _drop_column_once("cargos", "desconto_transporte_valor")
    _drop_column_once("cargos", "inss_funcionario_valor")
    _drop_column_once("cargos", "inss_funcionario_percentual")
    _drop_column_once("cargos", "gera_encargos")
    _drop_column_once("cargos", "regime_remuneracao")
