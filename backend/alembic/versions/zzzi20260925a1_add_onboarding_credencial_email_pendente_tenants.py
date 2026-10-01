"""add onboarding_credencial_email_pendente to tenants

Revision ID: zzzi20260925a1
Revises: zzzh20260923a1
Create Date: 2026-09-25

Adiciona `onboarding_credencial_email_pendente` em `tenants`: marcado quando
o onboarding assistido de ops cria a(s) loja(s) normalmente, mas o e-mail de
definicao de senha do titular nao pode ser enviado (ex.: SMTP indisponivel).
Antes disso bloqueava a criacao inteira (rollback); agora a loja nasce mesmo
assim, e esse flag deixa o time de ops ciente na propria lista de tenants
(entra como motivo "critical" no calculo de atencao — ver
app/services/ops_tenants_read_service.py) de que precisa repassar as
credenciais por outro canal.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zzzi20260925a1"
down_revision: Union[str, Sequence[str], None] = "zzzh20260923a1"
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
        "tenants",
        sa.Column(
            "onboarding_credencial_email_pendente",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    _drop_column_once("tenants", "onboarding_credencial_email_pendente")
