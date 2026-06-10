"""dre_periodos: re-backfill tenant_id (via usuario->users) + NOT NULL -> TenantScoped

A tabela ``dre_periodos`` (modelo ``DREPeriodo``, app/ia/aba7_models.py) tinha ``tenant_id``
UUID NULLABLE, fora do filtro global de tenant. A migration ``of20260512a1`` ja adicionou a
coluna ``tenant_id`` (UUID nullable), os indices (``ix_dre_periodos_tenant_id`` etc.) e o
backfill inicial via ``usuario_id -> users.tenant_id``. Esta migration FECHA o ciclo:

1. Re-backfill idempotente do ``tenant_id`` a partir do dono (``usuario_id -> users.tenant_id``),
   so para linhas que ainda estejam com ``tenant_id`` nulo (cobre periodos criados entre as duas
   migrations).
2. Torna ``tenant_id`` NOT NULL, alinhando ao mixin ``TenantScoped`` que o modelo passa a adotar
   (UUID NOT NULL, indexado — mesmo indice ``ix_dre_periodos_tenant_id`` ja existente; sem novo
   indice). Se sobrar orfa (``usuario_id`` nulo ou usuario sem tenant), o SET NOT NULL falha de
   proposito, evitando linha sem dono (mesma postura defensiva de pm20260609a1).

Pre-requisito do TenantScoped: o filtro global injeta ``AND tenant_id = <contexto>`` e colapsa o
``OR`` do helper ``buscar_periodo_dre_do_tenant`` — qualquer linha com ``tenant_id`` nulo
desapareceria. Por isso o backfill 100% e' obrigatorio ANTES do NOT NULL.

Validado read-only em producao: ``dre_periodos`` esta VAZIA (0 linhas) — backfill e NOT NULL sao
no-op de dados em prod, so selam o schema.

Revision ID: pn20260610a1
Revises: pm20260609a1
Create Date: 2026-06-10 14:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "pn20260610a1"
down_revision: Union[str, None] = "pm20260609a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "dre_periodos"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if TABELA not in insp.get_table_names():
        return

    colunas = {c["name"]: c for c in insp.get_columns(TABELA)}
    if "tenant_id" not in colunas:
        return

    # 1. Re-backfill idempotente: tenant_id a partir do dono (usuario_id -> users.tenant_id).
    #    So toca linhas nulas. Dialect-aware (Postgres: UPDATE..FROM; demais: subquery).
    if "users" in insp.get_table_names():
        if bind.dialect.name == "postgresql":
            op.execute(
                sa.text(
                    "UPDATE dre_periodos dp "
                    "SET tenant_id = u.tenant_id "
                    "FROM users u "
                    "WHERE dp.usuario_id = u.id "
                    "  AND dp.tenant_id IS NULL "
                    "  AND u.tenant_id IS NOT NULL"
                )
            )
        else:
            op.execute(
                sa.text(
                    "UPDATE dre_periodos "
                    "SET tenant_id = ("
                    "    SELECT u.tenant_id FROM users u "
                    "    WHERE u.id = dre_periodos.usuario_id AND u.tenant_id IS NOT NULL"
                    ") "
                    "WHERE tenant_id IS NULL AND usuario_id IS NOT NULL "
                    "  AND EXISTS ("
                    "    SELECT 1 FROM users u "
                    "    WHERE u.id = dre_periodos.usuario_id AND u.tenant_id IS NOT NULL"
                    "  )"
                )
            )

    # 2. NOT NULL — so se ainda for nullable (idempotente). Se sobrar orfa (esperado 0 em prod),
    #    o SET NOT NULL falha de proposito, evitando linha sem dono.
    tenant_col = colunas.get("tenant_id")
    if tenant_col is not None and tenant_col.get("nullable", True):
        op.alter_column(
            TABELA,
            "tenant_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if TABELA not in insp.get_table_names():
        return
    colunas = {c["name"]: c for c in insp.get_columns(TABELA)}
    tenant_col = colunas.get("tenant_id")
    if tenant_col is not None and not tenant_col.get("nullable", True):
        op.alter_column(
            TABELA,
            "tenant_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )
