"""RLS: produto_identidades visivel e editavel pelas lojas do mesmo grupo comercial

Revision ID: zzzzb20261015a1
Revises: zzzza20261015a1
Create Date: 2026-10-15

Tabela nova (sem dado de producao ainda em uso por nenhum consumidor), entao a
politica final de grupo ja entra direto, sem passar pelo estagio intermediario
"so a propria loja" que clientes/pets tiveram historicamente. Leitura e escrita
(UPDATE): propria loja OU loja do mesmo grupo comercial ativo da loja de origem
(mesmo _grupo_guard de zzzv20261005a1_rls_grupo_pessoas_pets.py, sem o guard de
parceiro veterinario — identidade de produto nao e compartilhada com clinicas
parceiras, so entre lojas do mesmo grupo). INSERT e DELETE continuam so da
propria loja.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "zzzzb20261015a1"
down_revision: Union[str, None] = "zzzza20261015a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABELA = "produto_identidades"
_LOJA_ATUAL = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
_PROPRIA = f"{_TABELA}.tenant_id = {_LOJA_ATUAL}"
_GRUPO_GUARD = f"""EXISTS (
    SELECT 1
    FROM grupo_comercial_membros m_eu
    JOIN grupo_comercial_membros m_origem ON m_origem.grupo_id = m_eu.grupo_id
    JOIN grupos_comerciais g ON g.id = m_eu.grupo_id
    WHERE replace(m_eu.empresa_id::text, '-', '') = replace({_LOJA_ATUAL}::text, '-', '')
      AND replace(m_origem.empresa_id::text, '-', '') = replace({_TABELA}.origem_tenant_id::text, '-', '')
      AND m_eu.status = 'ativo' AND m_origem.status = 'ativo' AND g.status = 'ativo'
)"""


def upgrade() -> None:
    op.execute(f"ALTER TABLE {_TABELA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {_TABELA} FORCE ROW LEVEL SECURITY")

    op.execute(
        f"CREATE POLICY {_TABELA}_grupo_select ON {_TABELA} FOR SELECT "
        f"USING ({_PROPRIA} OR {_GRUPO_GUARD})"
    )
    op.execute(
        f"CREATE POLICY {_TABELA}_tenant_insert ON {_TABELA} FOR INSERT "
        f"WITH CHECK ({_PROPRIA})"
    )
    op.execute(
        f"CREATE POLICY {_TABELA}_grupo_update ON {_TABELA} FOR UPDATE "
        f"USING ({_PROPRIA} OR {_GRUPO_GUARD}) WITH CHECK ({_PROPRIA} OR {_GRUPO_GUARD})"
    )
    op.execute(
        f"CREATE POLICY {_TABELA}_tenant_delete ON {_TABELA} FOR DELETE "
        f"USING ({_PROPRIA})"
    )


def downgrade() -> None:
    for politica in (
        f"{_TABELA}_tenant_delete",
        f"{_TABELA}_grupo_update",
        f"{_TABELA}_tenant_insert",
        f"{_TABELA}_grupo_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {politica} ON {_TABELA}")
    op.execute(f"ALTER TABLE {_TABELA} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {_TABELA} DISABLE ROW LEVEL SECURITY")
