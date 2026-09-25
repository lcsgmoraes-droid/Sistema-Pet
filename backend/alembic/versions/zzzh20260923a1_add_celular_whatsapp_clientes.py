"""add celular_whatsapp to clientes

Revision ID: zzzh20260923a1
Revises: zzzg20260922a1
Create Date: 2026-09-23

Adiciona `celular_whatsapp` (o celular também é WhatsApp?) em `clientes`.
Até aqui esse dado só existia como toggle visual na tela de Pessoa (aba
Contatos) e no cadastro de Usuário — nunca era realmente gravado (o valor
era descartado antes do PUT/POST). Esta coluna passa a persistir de
verdade; ver .claude/skills/pessoas/SKILL.md.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zzzh20260923a1"
down_revision: Union[str, Sequence[str], None] = "zzzg20260922a1"
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
        sa.Column("celular_whatsapp", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    _drop_column_once("clientes", "celular_whatsapp")
