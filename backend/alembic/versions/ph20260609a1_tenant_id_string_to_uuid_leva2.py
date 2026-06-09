"""tenant_id String -> UUID em 4 tabelas (Leva 2 multi-tenant)

Converte a coluna tenant_id de texto para UUID em data_subject_requests,
assinaturas_modulos e ecommerce_notify_requests, para que adotem o mixin
TenantScoped (filtro global de tenant + fail-fast).
Os valores ja estao em formato UUID (validado em producao antes do deploy);
o cast tenant_id::uuid e seguro. O Postgres reconstroi os indices da coluna
automaticamente na mudanca de tipo.

Revision ID: ph20260609a1
Revises: pg20260604a1
Create Date: 2026-06-09 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ph20260609a1"
down_revision: Union[str, None] = "pg20260604a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (tabela, tipo_texto_original) — o tipo de texto original e usado como
# existing_type no upgrade e como destino no downgrade.
_TABELAS = (
    ("data_subject_requests", sa.String(length=64)),
    ("assinaturas_modulos", sa.String(length=36)),
    ("ecommerce_notify_requests", sa.String(length=36)),
)


def upgrade() -> None:
    for tabela, tipo_texto in _TABELAS:
        op.alter_column(
            tabela,
            "tenant_id",
            existing_type=tipo_texto,
            type_=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
            postgresql_using="tenant_id::uuid",
        )


def downgrade() -> None:
    for tabela, tipo_texto in _TABELAS:
        op.alter_column(
            tabela,
            "tenant_id",
            existing_type=postgresql.UUID(as_uuid=True),
            type_=tipo_texto,
            existing_nullable=False,
            postgresql_using="tenant_id::text",
        )
