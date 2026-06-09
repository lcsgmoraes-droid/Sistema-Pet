"""tenant_id String -> UUID em pedidos e pedido_itens (Leva 3 multi-tenant)

Converte a coluna tenant_id de texto para UUID em pedidos e pedido_itens, para
que adotem o mixin TenantScoped (filtro global de tenant + fail-fast). Os valores
ja sao UUID-validos (validado em producao antes do deploy); o cast tenant_id::uuid
e seguro. O Postgres reconstroi os indices da coluna automaticamente.

Pre-requisito de codigo (mesmo PR): a rota ecommerce.checkout_real passou a chamar
set_current_tenant antes de consultar Pedido (checkout_service), evitando fail-fast.

Revision ID: pi20260609a1
Revises: ph20260609a1
Create Date: 2026-06-09 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "pi20260609a1"
down_revision: Union[str, None] = "ph20260609a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABELAS = (
    ("pedidos", sa.String(length=36)),
    ("pedido_itens", sa.String(length=36)),
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
