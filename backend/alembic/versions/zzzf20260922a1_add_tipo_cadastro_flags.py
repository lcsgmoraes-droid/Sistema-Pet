"""add multi-tipo cadastro flags to clientes

Revision ID: zzzf20260922a1
Revises: zzze20260922a1
Create Date: 2026-09-22

Adiciona is_cliente/is_fornecedor/is_veterinario/is_funcionario como flags
booleanas independentes, permitindo que uma pessoa acumule varios tipos ao
mesmo tempo. A coluna tipo_cadastro (valor unico) fica obsoleta a partir
desta mudanca — ver Documentacao/Dominio/Cliente.md e
.claude/skills/pessoas/SKILL.md — mas nao e alterada nem removida aqui:
continua preenchida por compatibilidade com consumidores ainda nao
migrados. O backfill de dados fica na migration seguinte
(zzzg20260922a1_backfill_tipo_cadastro_flags).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zzzf20260922a1"
down_revision: Union[str, Sequence[str], None] = "zzze20260922a1"
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
    _add_column_once(
        "clientes",
        sa.Column("is_cliente", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _add_column_once(
        "clientes",
        sa.Column("is_fornecedor", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _add_column_once(
        "clientes",
        sa.Column("is_veterinario", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _add_column_once(
        "clientes",
        sa.Column("is_funcionario", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    _drop_column_once("clientes", "is_funcionario")
    _drop_column_once("clientes", "is_veterinario")
    _drop_column_once("clientes", "is_fornecedor")
    _drop_column_once("clientes", "is_cliente")
