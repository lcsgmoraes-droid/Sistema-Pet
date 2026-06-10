"""create variacao_config_fiscal (tenant_id UUID) — idempotente

A tabela ``variacao_config_fiscal`` nunca entrou no Alembic (nem no env.py), apesar
de o modelo existir e ser consultado por serviços. Esta migration a coloca sob
controle do Alembic, já com ``tenant_id`` UUID (o modelo tinha o bug de declará-lo
como Integer).

Idempotente para cobrir os dois cenários reais:
- Produção (Alembic puro): a tabela não existe -> cria com tenant_id UUID.
- Ambientes legados criados via ``Base.metadata.create_all`` quando o modelo ainda
  usava Integer: a tabela já existe com tenant_id Integer -> converte para UUID se
  estiver vazia; se houver linhas (valores Integer não convertem para UUID), aborta
  com mensagem clara em vez de destruir/baguncar dados.

Revision ID: pk20260609a1
Revises: pi20260609a1
Create Date: 2026-06-08 17:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "pk20260609a1"
down_revision: Union[str, None] = "pi20260609a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "variacao_config_fiscal"
IX_TENANT = "ix_variacao_config_fiscal_tenant_id"


def _criar_tabela() -> None:
    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("variacao_id", sa.Integer(), nullable=False),
        sa.Column("produto_config_fiscal_id", sa.Integer(), nullable=True),
        sa.Column("herdado_do_produto", sa.Boolean(), nullable=False),
        sa.Column("ncm", sa.String(length=10), nullable=True),
        sa.Column("cest", sa.String(length=10), nullable=True),
        sa.Column("origem_mercadoria", sa.String(length=1), nullable=True),
        sa.Column("cst_icms", sa.String(length=3), nullable=True),
        sa.Column("icms_aliquota", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("icms_st", sa.Boolean(), nullable=True),
        sa.Column("cfop_venda", sa.String(length=4), nullable=True),
        sa.Column("cfop_compra", sa.String(length=4), nullable=True),
        sa.Column("pis_cst", sa.String(length=3), nullable=True),
        sa.Column("pis_aliquota", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("cofins_cst", sa.String(length=3), nullable=True),
        sa.Column("cofins_aliquota", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("observacao_fiscal", sa.Text(), nullable=True),
        sa.Column("configuracao_sugerida", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        # produto_variacao NÃO tem modelo/tabela mapeada no projeto, portanto
        # variacao_id fica sem ForeignKey (apenas UNIQUE), como em kit_composicao.
        sa.ForeignKeyConstraint(["produto_config_fiscal_id"], ["produto_config_fiscal.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variacao_id"),
    )
    op.create_index(op.f(IX_TENANT), TABELA, ["tenant_id"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if TABELA not in insp.get_table_names():
        _criar_tabela()
        return

    # Tabela já existe (criada por create_all legado). Alinhar tenant_id -> UUID.
    colunas = {c["name"]: c for c in insp.get_columns(TABELA)}
    tenant_col = colunas.get("tenant_id")

    if tenant_col is not None and "UUID" not in str(tenant_col["type"]).upper():
        total = (
            bind.execute(
                sa.text(f"SELECT COUNT(*) FROM {TABELA} WHERE tenant_id IS NOT NULL")
            ).scalar()
            or 0
        )
        if total:
            raise RuntimeError(
                f"{TABELA} possui {total} linha(s) com tenant_id Integer, que não "
                "convertem automaticamente para UUID. Trate os dados manualmente "
                "(mapear para o UUID do tenant correto ou remover órfãos) e re-rode "
                "esta migration."
            )
        op.alter_column(
            TABELA,
            "tenant_id",
            type_=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
            postgresql_using="tenant_id::text::uuid",
        )

    indices = {ix["name"] for ix in insp.get_indexes(TABELA)}
    if IX_TENANT not in indices:
        op.create_index(op.f(IX_TENANT), TABELA, ["tenant_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if TABELA in insp.get_table_names():
        indices = {ix["name"] for ix in insp.get_indexes(TABELA)}
        if IX_TENANT in indices:
            op.drop_index(op.f(IX_TENANT), table_name=TABELA)
        op.drop_table(TABELA)
