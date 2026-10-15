"""produto_identidades: schema aditivo da identidade compartilhada de produto (fase D)

Revision ID: zzzza20261015a1
Revises: zzzz20261013a1
Create Date: 2026-10-15

Aditiva, sem RLS ainda e sem mudanca de comportamento (RLS entra na proxima
migration). Cria produto_identidades + historico, o FK nullable
produtos.produto_identidade_id (com indice unico parcial por tenant) e as duas
tabelas de apoio (conflitos de correspondencia e execucoes da varredura de
reconciliacao). Ver Documentacao/Dominio/Plano-Camada-Geral.md, Checkpoint 7.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "zzzza20261015a1"
down_revision: Union[str, None] = "zzzz20261013a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "produto_identidades",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("origem_tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("descricao_curta", sa.Text(), nullable=True),
        sa.Column("descricao_completa", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("codigo_barras", sa.String(length=20), nullable=True),
        sa.Column("codigos_barras_alternativos", sa.Text(), nullable=True),
        sa.Column("gtin_ean", sa.String(length=20), nullable=True),
        sa.Column("gtin_ean_tributario", sa.String(length=20), nullable=True),
        sa.Column("chave_matching", sa.String(length=20), nullable=True),
        sa.Column("unidade", sa.String(length=10), nullable=True),
        sa.Column("condicao", sa.String(length=20), nullable=True),
        sa.Column("e_granel", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("producao", sa.String(length=20), nullable=True),
        sa.Column("peso_liquido", sa.Float(), nullable=True),
        sa.Column("peso_bruto", sa.Float(), nullable=True),
        sa.Column("largura", sa.Float(), nullable=True),
        sa.Column("altura", sa.Float(), nullable=True),
        sa.Column("profundidade", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("itens_por_caixa", sa.Integer(), nullable=True),
        sa.Column("imagem_principal", sa.String(length=255), nullable=True),
        sa.Column("especie_compativel", sa.String(length=50), nullable=True),
        sa.Column("classificacao_racao", sa.String(length=50), nullable=True),
        sa.Column("peso_embalagem", sa.Float(), nullable=True),
        sa.Column("tabela_nutricional", sa.Text(), nullable=True),
        sa.Column("categoria_racao", sa.String(length=50), nullable=True),
        sa.Column("especies_indicadas", sa.String(length=100), nullable=True),
        sa.Column("tabela_consumo", sa.Text(), nullable=True),
        sa.Column("porte_animal", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fase_publico", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tipo_tratamento", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sabor_proteina", sa.String(length=100), nullable=True),
        sa.Column("auto_classificar_nome", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_produto_identidades_tenant_id", "produto_identidades", ["tenant_id"])
    op.create_index("ix_produto_identidades_origem_tenant_id", "produto_identidades", ["origem_tenant_id"])
    op.create_index("ix_produto_identidades_chave_matching", "produto_identidades", ["chave_matching"])

    op.create_table(
        "produto_identidades_historico_alteracoes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "produto_identidade_id",
            sa.Integer(),
            sa.ForeignKey("produto_identidades.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campo", sa.String(length=100), nullable=False),
        sa.Column("valor_anterior", sa.Text(), nullable=True),
        sa.Column("valor_novo", sa.Text(), nullable=True),
        sa.Column(
            "alterado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_produto_identidades_historico_tenant_id",
        "produto_identidades_historico_alteracoes",
        ["tenant_id"],
    )
    op.create_index(
        "ix_produto_identidades_historico_identidade_id",
        "produto_identidades_historico_alteracoes",
        ["produto_identidade_id"],
    )

    op.add_column(
        "produtos",
        sa.Column(
            "produto_identidade_id",
            sa.Integer(),
            sa.ForeignKey("produto_identidades.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_produtos_produto_identidade_id", "produtos", ["produto_identidade_id"])
    op.create_index(
        "ux_produtos_tenant_identidade",
        "produtos",
        ["tenant_id", "produto_identidade_id"],
        unique=True,
        postgresql_where=sa.text("produto_identidade_id IS NOT NULL AND deleted_at IS NULL"),
    )

    op.create_table(
        "produto_identidade_conflitos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "grupo_id",
            sa.Integer(),
            sa.ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chave_matching", sa.String(length=20), nullable=False),
        sa.Column("produto_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "detectado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolvido", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "resolvido_por_usuario_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolvido_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_produto_identidade_conflitos_grupo_id", "produto_identidade_conflitos", ["grupo_id"]
    )

    op.create_table(
        "produto_identidade_backfill_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "grupo_id",
            sa.Integer(),
            sa.ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "executado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("total_produtos_ativos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_com_gtin", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_identidades_criadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_vinculados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sem_gtin", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_conflitos", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_produto_identidade_backfill_runs_grupo_id",
        "produto_identidade_backfill_runs",
        ["grupo_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_produto_identidade_backfill_runs_grupo_id", table_name="produto_identidade_backfill_runs")
    op.drop_table("produto_identidade_backfill_runs")

    op.drop_index("ix_produto_identidade_conflitos_grupo_id", table_name="produto_identidade_conflitos")
    op.drop_table("produto_identidade_conflitos")

    op.drop_index("ux_produtos_tenant_identidade", table_name="produtos")
    op.drop_index("ix_produtos_produto_identidade_id", table_name="produtos")
    op.drop_column("produtos", "produto_identidade_id")

    op.drop_index(
        "ix_produto_identidades_historico_identidade_id",
        table_name="produto_identidades_historico_alteracoes",
    )
    op.drop_index(
        "ix_produto_identidades_historico_tenant_id",
        table_name="produto_identidades_historico_alteracoes",
    )
    op.drop_table("produto_identidades_historico_alteracoes")

    op.drop_index("ix_produto_identidades_chave_matching", table_name="produto_identidades")
    op.drop_index("ix_produto_identidades_origem_tenant_id", table_name="produto_identidades")
    op.drop_index("ix_produto_identidades_tenant_id", table_name="produto_identidades")
    op.drop_table("produto_identidades")
