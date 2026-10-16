"""RLS: pessoas e pets visiveis e editaveis pelas lojas do mesmo grupo comercial

Revision ID: zzzv20261005a1
Revises: zzzu20261005a1
Create Date: 2026-10-05

Leitura: propria loja, parceiro veterinario (como antes) ou loja do mesmo grupo
comercial da loja de origem. Escrita (UPDATE): mesma regra. INSERT e DELETE
continuam so da propria loja (exclusao logica fica restrita a origem pela aplicacao).
Produtos nao entram nesta migration (cadastro base compartilhado, fase D).
"""

from typing import Sequence, Union

from alembic import op


revision: str = "zzzv20261005a1"
down_revision: Union[str, None] = "zzzu20261005a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LOJA_ATUAL = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _grupo_guard(tabela: str) -> str:
    return f"""EXISTS (
        SELECT 1
        FROM grupo_comercial_membros m_eu
        JOIN grupo_comercial_membros m_origem ON m_origem.grupo_id = m_eu.grupo_id
        JOIN grupos_comerciais g ON g.id = m_eu.grupo_id
        WHERE replace(m_eu.empresa_id::text, '-', '') = replace({_LOJA_ATUAL}::text, '-', '')
          AND replace(m_origem.empresa_id::text, '-', '') = replace({tabela}.origem_tenant_id::text, '-', '')
          AND m_eu.status = 'ativo' AND m_origem.status = 'ativo' AND g.status = 'ativo'
    )"""


def _vet_guard(tabela: str) -> str:
    return f"""EXISTS (
        SELECT 1 FROM vet_partner_link vpl
        WHERE vpl.empresa_tenant_id = {tabela}.tenant_id
          AND vpl.vet_tenant_id = {_LOJA_ATUAL}
          AND vpl.ativo = true
    )"""


def _propria(tabela: str) -> str:
    return f"{tabela}.tenant_id = {_LOJA_ATUAL}"


def upgrade() -> None:
    for tabela in ("clientes", "pets"):
        op.execute(f"DROP POLICY IF EXISTS {tabela}_partner_select ON {tabela}")
        op.execute(
            f"CREATE POLICY {tabela}_grupo_select ON {tabela} FOR SELECT USING "
            f"({_propria(tabela)} OR {_vet_guard(tabela)} OR {_grupo_guard(tabela)})"
        )
        op.execute(f"DROP POLICY IF EXISTS {tabela}_tenant_update ON {tabela}")
        op.execute(
            f"CREATE POLICY {tabela}_grupo_update ON {tabela} FOR UPDATE "
            f"USING ({_propria(tabela)} OR {_grupo_guard(tabela)}) "
            f"WITH CHECK ({_propria(tabela)} OR {_grupo_guard(tabela)})"
        )


def downgrade() -> None:
    for tabela in ("clientes", "pets"):
        op.execute(f"DROP POLICY IF EXISTS {tabela}_grupo_select ON {tabela}")
        op.execute(
            f"CREATE POLICY {tabela}_partner_select ON {tabela} FOR SELECT USING "
            f"({_propria(tabela)} OR {_vet_guard(tabela)})"
        )
        op.execute(f"DROP POLICY IF EXISTS {tabela}_grupo_update ON {tabela}")
        op.execute(
            f"CREATE POLICY {tabela}_tenant_update ON {tabela} FOR UPDATE "
            f"USING ({_propria(tabela)}) WITH CHECK ({_propria(tabela)})"
        )
