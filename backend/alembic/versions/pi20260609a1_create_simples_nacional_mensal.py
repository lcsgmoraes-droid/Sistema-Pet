"""create simples_nacional_mensal (tenant_id UUID) — idempotente

A tabela ``simples_nacional_mensal`` nunca entrou no Alembic, apesar de o modelo
``SimplesNacionalMensal`` existir desde o commit inicial e ser consultado por rotas
e serviços (``simples_routes``, ``fechamento_simples_service`` e, sobretudo,
``projecao_caixa_service``). Em produção (Alembic puro, sem ``create_all`` no
startup) a tabela simplesmente NÃO existe — confirmado por checagem read-only —
então toda query a ela quebra com "relation does not exist". O impacto vivo é a
página ``/projecao-caixa`` (gated por ``financeiro_erp``), que consulta a tabela sem
guarda; as rotas ``/simples/*`` também quebrariam, mas hoje têm a UI desativada.

Esta migration coloca a tabela sob controle do Alembic já com ``tenant_id`` UUID,
alinhada ao mixin ``TenantScoped`` adotado pelo modelo (mesmo padrão da Leva 2).

Idempotente para cobrir os dois cenários reais:
- Produção (Alembic puro): a tabela não existe -> cria com ``tenant_id`` UUID.
- Ambientes legados criados via ``Base.metadata.create_all`` quando o modelo ainda
  declarava ``tenant_id`` como String: a tabela já existe -> converte a coluna para
  UUID (cast ``tenant_id::uuid``; valores em formato UUID) e garante índice/unique.

Revision ID: pi20260609a1
Revises: pj20260609a1
Create Date: 2026-06-09 17:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "pi20260609a1"
# down_revision = pj20260609a1: a Leva 3 (#325, pedidos) mergeou ANTES desta; encadeio
# sobre a head resultante (pj) para manter um head unico (ph -> pj -> pi) e evitar que
# `alembic upgrade head` falhe com multiplos heads.
down_revision: Union[str, None] = "pj20260609a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "simples_nacional_mensal"
IX_TENANT = "ix_simples_nacional_mensal_tenant_id"
UQ_COMPETENCIA = "uq_simples_mensal_competencia"


def _criar_tabela() -> None:
    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column(
            "faturamento_sistema",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
            comment="Apurado via NF do sistema",
        ),
        sa.Column(
            "faturamento_contador",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
            comment="Informado manualmente pelo contador (prioritário)",
        ),
        sa.Column(
            "imposto_estimado",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
            comment="Provisões acumuladas no mês",
        ),
        sa.Column(
            "imposto_real",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
            comment="Valor real do DAS pago",
        ),
        sa.Column(
            "aliquota_efetiva",
            sa.Numeric(precision=6, scale=4),
            nullable=True,
            comment="Alíquota real calculada (imposto/faturamento)",
        ),
        sa.Column(
            "aliquota_sugerida",
            sa.Numeric(precision=6, scale=4),
            nullable=True,
            comment="Sugestão para próximo mês",
        ),
        sa.Column("fechado", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "ano", "mes", name=UQ_COMPETENCIA),
    )
    op.create_index(op.f(IX_TENANT), TABELA, ["tenant_id"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if TABELA not in insp.get_table_names():
        _criar_tabela()
        return

    # Tabela já existe (criada por create_all legado, tenant_id String).
    # Alinhar tenant_id -> UUID e garantir índice/unique (idempotente).
    colunas = {c["name"]: c for c in insp.get_columns(TABELA)}
    tenant_col = colunas.get("tenant_id")
    if tenant_col is not None and "UUID" not in str(tenant_col["type"]).upper():
        op.alter_column(
            TABELA,
            "tenant_id",
            type_=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
            postgresql_using="tenant_id::uuid",
        )

    indices = {ix["name"] for ix in insp.get_indexes(TABELA)}
    if IX_TENANT not in indices:
        op.create_index(op.f(IX_TENANT), TABELA, ["tenant_id"], unique=False)

    uniques = {uc["name"] for uc in insp.get_unique_constraints(TABELA)}
    if UQ_COMPETENCIA not in uniques:
        op.create_unique_constraint(UQ_COMPETENCIA, TABELA, ["tenant_id", "ano", "mes"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if TABELA in insp.get_table_names():
        indices = {ix["name"] for ix in insp.get_indexes(TABELA)}
        if IX_TENANT in indices:
            op.drop_index(op.f(IX_TENANT), table_name=TABELA)
        op.drop_table(TABELA)
