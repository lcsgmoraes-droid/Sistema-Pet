"""comissoes_itens: backfill tenant_id (via venda) + NOT NULL -> TenantScoped

A tabela ``comissoes_itens`` (modelo ``ComissaoItem``, app/comissoes_models.py) tinha
``tenant_id`` UUID NULLABLE, fora do filtro global de tenant. Esta migration:

1. Faz backfill do ``tenant_id`` a partir da venda relacionada (``vendas.tenant_id`` e
   NOT NULL; ``comissoes_itens.venda_id`` e FK obrigatoria) — idempotente, so preenche
   linhas com ``tenant_id`` nulo.
2. Torna ``tenant_id`` NOT NULL, alinhando ao mixin ``TenantScoped`` que o modelo passa
   a adotar (UUID NOT NULL, indexado — mesmo indice ``ix_comissoes_itens_tenant_id`` ja
   existente; sem novo indice).

Validado read-only em producao (2026-06-09): ``comissoes_itens`` tem 3 linhas, todas ja
com ``tenant_id``; 0 orfas (sem venda ou venda sem tenant). O backfill e no-op em prod.

Revision ID: pm20260609a1
Revises: pl20260609a1
Create Date: 2026-06-09 23:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "pm20260609a1"
down_revision: Union[str, None] = "pl20260609a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "comissoes_itens"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if TABELA not in insp.get_table_names():
        return

    # 1. Backfill tenant_id a partir da venda (idempotente: so toca linhas nulas).
    op.execute(
        sa.text(
            "UPDATE comissoes_itens "
            "SET tenant_id = (SELECT v.tenant_id FROM vendas v WHERE v.id = comissoes_itens.venda_id) "
            "WHERE tenant_id IS NULL"
        )
    )

    # 2. NOT NULL — so se ainda for nullable (idempotente). Se sobrar orfa (esperado 0),
    #    o SET NOT NULL falha de proposito, evitando linha sem dono.
    colunas = {c["name"]: c for c in insp.get_columns(TABELA)}
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
