"""Renomeia EmpresaGrupo para GrupoComercial (tabelas, indices, constraints).

Puro DDL — nenhuma linha de dado e tocada aqui (o backfill de grupos-de-1
para tenants que ainda nao tem grupo fica na proxima migration, de
proposito, para que rename e backfill possam ser avaliados/revertidos
independentemente um do outro).

FKs de outras tabelas (ex. venda_itens.estoque_compartilhado_id) nao
precisam de passo proprio aqui: o Postgres segue o OID da tabela, nao o
nome, entao continuam apontando certo depois do rename. O mesmo vale, em
teoria, pela politica de RLS `produtos_grupo_estoque_select` (expressao
compilada por OID) — mesmo assim ela e recriada aqui explicitamente contra
os nomes novos, por seguranca, ja que e um objeto sensivel de isolamento de
dado e nao vale a pena confiar cegamente nisso sem um ambiente Postgres
real para validar.

Constraints de FK sem nome explicito (auto-geradas pelo Postgres a partir
do nome antigo da tabela, ex. `empresa_grupo_membros_grupo_id_fkey`) nao
sao renomeadas aqui — decisao consciente: sao só cosmeticas, ninguem no
codigo da aplicacao referencia esse nome, e descobrir o nome exato geraria
uma dependencia de introspeccao do banco real que nao vale o risco.

Revision ID: zzw20260918a1
Revises: zzv20260917a1
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "zzw20260918a1"
down_revision = "zzv20260917a1"
branch_labels = None
depends_on = None


TABELAS = [
    ("empresa_grupos", "grupos_comerciais"),
    ("empresa_grupo_membros", "grupo_comercial_membros"),
    ("empresa_grupo_codigos", "grupo_comercial_codigos"),
    ("empresa_grupo_convites", "grupo_comercial_convites"),
    ("empresa_grupo_transferencias", "grupo_comercial_transferencias"),
    ("empresa_grupo_produto_vinculos", "grupo_comercial_produto_vinculos"),
    (
        "empresa_grupo_estoques_compartilhados",
        "grupo_comercial_estoques_compartilhados",
    ),
]

CHECK_CONSTRAINTS = [
    ("grupos_comerciais", "ck_empresa_grupos_status", "ck_grupos_comerciais_status"),
    (
        "grupo_comercial_membros",
        "ck_empresa_grupo_membros_papel",
        "ck_grupo_comercial_membros_papel",
    ),
    (
        "grupo_comercial_membros",
        "ck_empresa_grupo_membros_status",
        "ck_grupo_comercial_membros_status",
    ),
    (
        "grupo_comercial_convites",
        "ck_empresa_grupo_convites_status",
        "ck_grupo_comercial_convites_status",
    ),
    (
        "grupo_comercial_transferencias",
        "ck_empresa_grupo_transferencias_empresas_distintas",
        "ck_grupo_comercial_transferencias_empresas_distintas",
    ),
    (
        "grupo_comercial_transferencias",
        "ck_empresa_grupo_transferencias_status",
        "ck_grupo_comercial_transferencias_status",
    ),
    (
        "grupo_comercial_produto_vinculos",
        "ck_empresa_grupo_produto_vinculos_empresas_distintas",
        "ck_grupo_comercial_produto_vinculos_empresas_distintas",
    ),
    (
        "grupo_comercial_produto_vinculos",
        "ck_empresa_grupo_produto_vinculos_produtos_positivos",
        "ck_grupo_comercial_produto_vinculos_produtos_positivos",
    ),
    (
        "grupo_comercial_produto_vinculos",
        "ck_empresa_grupo_produto_vinculos_status",
        "ck_grupo_comercial_produto_vinculos_status",
    ),
    (
        "grupo_comercial_estoques_compartilhados",
        "ck_empresa_grupo_estoque_empresas_distintas",
        "ck_grupo_comercial_estoque_empresas_distintas",
    ),
    (
        "grupo_comercial_estoques_compartilhados",
        "ck_empresa_grupo_estoque_status",
        "ck_grupo_comercial_estoque_status",
    ),
]

UNIQUE_CONSTRAINTS = [
    (
        "grupo_comercial_membros",
        "uq_empresa_grupo_membro_empresa",
        "uq_grupo_comercial_membro_empresa",
    ),
    (
        "grupo_comercial_codigos",
        "uq_empresa_grupo_codigos_codigo",
        "uq_grupo_comercial_codigos_codigo",
    ),
    (
        "grupo_comercial_codigos",
        "uq_empresa_grupo_codigo_competencia",
        "uq_grupo_comercial_codigo_competencia",
    ),
    (
        "grupo_comercial_convites",
        "uq_empresa_grupo_convite_empresa",
        "uq_grupo_comercial_convite_empresa",
    ),
    (
        "grupo_comercial_transferencias",
        "uq_empresa_grupo_transferencia_idempotencia",
        "uq_grupo_comercial_transferencia_idempotencia",
    ),
    (
        "grupo_comercial_produto_vinculos",
        "uq_empresa_grupo_produto_vinculo_par",
        "uq_grupo_comercial_produto_vinculo_par",
    ),
    (
        "grupo_comercial_estoques_compartilhados",
        "uq_empresa_grupo_estoque_compartilhado",
        "uq_grupo_comercial_estoque_compartilhado",
    ),
]

INDEXES = [
    ("ix_empresa_grupo_membros_grupo_id", "ix_grupo_comercial_membros_grupo_id"),
    (
        "ix_empresa_grupo_membros_empresa_status",
        "ix_grupo_comercial_membros_empresa_status",
    ),
    ("ix_empresa_grupo_codigos_codigo", "ix_grupo_comercial_codigos_codigo"),
    (
        "ix_empresa_grupo_codigos_empresa_validade",
        "ix_grupo_comercial_codigos_empresa_validade",
    ),
    ("ix_empresa_grupo_convites_grupo_id", "ix_grupo_comercial_convites_grupo_id"),
    (
        "ix_empresa_grupo_convites_destino_status",
        "ix_grupo_comercial_convites_destino_status",
    ),
    (
        "ix_empresa_grupo_transferencias_grupo_criado",
        "ix_grupo_comercial_transferencias_grupo_criado",
    ),
    (
        "ix_empresa_grupo_transferencias_destino_criado",
        "ix_grupo_comercial_transferencias_destino_criado",
    ),
    (
        "ix_empresa_grupo_produto_vinculos_grupo_status",
        "ix_grupo_comercial_produto_vinculos_grupo_status",
    ),
    (
        "ix_empresa_grupo_estoque_compartilhado_consumidora_status",
        "ix_grupo_comercial_estoque_compartilhado_consumidora_status",
    ),
    (
        "ix_empresa_grupo_estoque_compartilhado_origem_status",
        "ix_grupo_comercial_estoque_compartilhado_origem_status",
    ),
]


def _recriar_politica_leitura_produtos_compartilhados(*, nomes_antigos: bool) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    estoque = (
        "empresa_grupo_estoques_compartilhados"
        if nomes_antigos
        else "grupo_comercial_estoques_compartilhados"
    )
    grupos = "empresa_grupos" if nomes_antigos else "grupos_comerciais"
    membros = "empresa_grupo_membros" if nomes_antigos else "grupo_comercial_membros"

    op.execute("DROP POLICY IF EXISTS produtos_grupo_estoque_select ON produtos")
    op.execute(
        f"""
        CREATE POLICY produtos_grupo_estoque_select ON produtos
        FOR SELECT USING (
            EXISTS (
                SELECT 1
                FROM {estoque} egec
                JOIN {grupos} eg
                  ON eg.id = egec.grupo_id
                 AND eg.status = 'ativo'
                JOIN {membros} egmo
                  ON egmo.grupo_id = egec.grupo_id
                 AND egmo.empresa_id::text = egec.empresa_origem_id::text
                 AND egmo.status = 'ativo'
                JOIN {membros} egmc
                  ON egmc.grupo_id = egec.grupo_id
                 AND egmc.empresa_id::text = egec.empresa_consumidora_id::text
                 AND egmc.status = 'ativo'
                WHERE egec.produto_origem_id = produtos.id
                  AND egec.empresa_origem_id::text = produtos.tenant_id::text
                  AND egec.empresa_consumidora_id::text =
                      NULLIF(current_setting('app.tenant_id', true), '')
                  AND egec.status = 'ativo'
            )
        )
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    postgres = bind.dialect.name == "postgresql"

    for nome_antigo, nome_novo in TABELAS:
        op.rename_table(nome_antigo, nome_novo)

    if postgres:
        for tabela, nome_antigo, nome_novo in CHECK_CONSTRAINTS:
            op.execute(
                f'ALTER TABLE {tabela} RENAME CONSTRAINT "{nome_antigo}" TO "{nome_novo}"'
            )
        for tabela, nome_antigo, nome_novo in UNIQUE_CONSTRAINTS:
            op.execute(
                f'ALTER TABLE {tabela} RENAME CONSTRAINT "{nome_antigo}" TO "{nome_novo}"'
            )
        for nome_antigo, nome_novo in INDEXES:
            op.execute(f'ALTER INDEX "{nome_antigo}" RENAME TO "{nome_novo}"')

    _recriar_politica_leitura_produtos_compartilhados(nomes_antigos=False)


def downgrade() -> None:
    bind = op.get_bind()
    postgres = bind.dialect.name == "postgresql"

    # Ordem importa: os nomes de tabela em CHECK_CONSTRAINTS/UNIQUE_CONSTRAINTS
    # sao os nomes NOVOS (grupo_comercial_*) — por isso index/constraint voltam
    # antes do rename de tabela, e a politica (que usa os nomes ANTIGOS) so
    # depois que as tabelas ja estiverem com o nome antigo de volta.
    if postgres:
        for nome_antigo, nome_novo in INDEXES:
            op.execute(f'ALTER INDEX "{nome_novo}" RENAME TO "{nome_antigo}"')
        for tabela, nome_antigo, nome_novo in UNIQUE_CONSTRAINTS:
            op.execute(
                f'ALTER TABLE {tabela} RENAME CONSTRAINT "{nome_novo}" TO "{nome_antigo}"'
            )
        for tabela, nome_antigo, nome_novo in CHECK_CONSTRAINTS:
            op.execute(
                f'ALTER TABLE {tabela} RENAME CONSTRAINT "{nome_novo}" TO "{nome_antigo}"'
            )

    for nome_antigo, nome_novo in TABELAS:
        op.rename_table(nome_novo, nome_antigo)

    _recriar_politica_leitura_produtos_compartilhados(nomes_antigos=True)
