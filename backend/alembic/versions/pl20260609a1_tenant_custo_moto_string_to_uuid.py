"""configuracoes_custo_moto: tenant_id String(36)->UUID + TenantScoped — idempotente

O modelo ``ConfiguracaoCustoMoto`` (app/models_configuracao_custo_moto.py) declarava
``tenant_id`` como ``FK -> tenants.id`` (String(36)), portanto fora do filtro global de
tenant. Esta migration alinha a coluna a UUID (o contexto de tenant é UUID) e remove a
FK para ``tenants.id`` (tipos incompatíveis: UUID vs varchar(36)). O ``UNIQUE`` ("um
config por loja") é preservado.

Idempotente para os dois cenários reais:
- Produção (Alembic puro): a tabela não existe -> cria com ``tenant_id`` UUID + unique.
- Ambientes legados (``Base.metadata.create_all`` com tenant_id String/FK): dropa a FK,
  converte ``tenant_id`` para UUID (cast ``tenant_id::uuid``; valores em formato UUID) e
  garante o unique.

Revision ID: pl20260609a1
Revises: pk20260609a1
Create Date: 2026-06-09 22:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "pl20260609a1"
down_revision: Union[str, None] = "pk20260609a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "configuracoes_custo_moto"
UQ_TENANT = "uq_configuracoes_custo_moto_tenant"


def _criar_tabela() -> None:
    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "preco_combustivel", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column("km_por_litro", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("km_troca_oleo", sa.Integer(), nullable=True),
        sa.Column("custo_troca_oleo", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("km_troca_pneu_dianteiro", sa.Integer(), nullable=True),
        sa.Column(
            "custo_pneu_dianteiro", sa.Numeric(precision=10, scale=2), nullable=True
        ),
        sa.Column("km_troca_pneu_traseiro", sa.Integer(), nullable=True),
        sa.Column(
            "custo_pneu_traseiro", sa.Numeric(precision=10, scale=2), nullable=True
        ),
        sa.Column("km_troca_kit_traseiro", sa.Integer(), nullable=True),
        sa.Column(
            "custo_kit_traseiro", sa.Numeric(precision=10, scale=2), nullable=True
        ),
        sa.Column("km_manutencao_geral", sa.Integer(), nullable=True),
        sa.Column(
            "custo_manutencao_geral", sa.Numeric(precision=10, scale=2), nullable=True
        ),
        sa.Column("seguro_mensal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "licenciamento_mensal", sa.Numeric(precision=10, scale=2), nullable=True
        ),
        sa.Column("ipva_mensal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "outros_custos_mensais", sa.Numeric(precision=10, scale=2), nullable=True
        ),
        sa.Column("km_medio_mensal", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name=UQ_TENANT),
    )


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if TABELA not in insp.get_table_names():
        _criar_tabela()
        return

    # Tabela já existe (create_all legado, tenant_id String/FK). Alinhar -> UUID.
    # 1. Dropar qualquer FK sobre tenant_id (UUID não referencia tenants.id varchar(36)).
    for fk in insp.get_foreign_keys(TABELA):
        if "tenant_id" in (fk.get("constrained_columns") or []) and fk.get("name"):
            op.drop_constraint(fk["name"], TABELA, type_="foreignkey")

    # 2. Converter tenant_id -> UUID se ainda não for.
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

    # 3. Garantir unique em tenant_id (a coluna era unique=True; se o constraint sumiu,
    #    recria com nome canônico).
    tem_unique = any(
        "tenant_id" in (uc.get("column_names") or [])
        for uc in insp.get_unique_constraints(TABELA)
    )
    if not tem_unique:
        op.create_unique_constraint(UQ_TENANT, TABELA, ["tenant_id"])


def downgrade() -> None:
    # Inverso conservador: reverte o tipo para varchar(36); não restaura a FK nem dropa
    # a tabela (evita destruir dados de uma tabela que podia pré-existir).
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if TABELA in insp.get_table_names():
        colunas = {c["name"]: c for c in insp.get_columns(TABELA)}
        tenant_col = colunas.get("tenant_id")
        if tenant_col is not None and "UUID" in str(tenant_col["type"]).upper():
            op.alter_column(
                TABELA,
                "tenant_id",
                type_=sa.String(length=36),
                existing_nullable=False,
                postgresql_using="tenant_id::text",
            )
