"""Remove produto_mestre (+ categoria/marca/departamento mestre): Produto passou
a ter identidade compartilhada automatica via produto_identidades (ver migrations
zzzza20261015a1/zzzzb20261015a1 e app/services/produto_identidade_service.py) -
correspondencia automatica por codigo de barras/GTIN dentro do grupo comercial,
em vez de vinculo opcional manual a um "produto-mestre" copiado uma unica vez.
Mesmo tratamento ja dado ao pessoa_mestre (migration zzzy20261009a1): 0 linhas em
producao em produto_mestre/categoria_mestre/marca_mestre/departamento_mestre e em
produtos.produto_mestre_id. Removido junto com os models `ProdutoMestre`/
`CategoriaMestre`/`MarcaMestre`/`DepartamentoMestre`, o service e as rotas
`/produto-mestre`.

Revision ID: zzzzc20261015a1
Revises: zzzzb20261015a1
Create Date: 2026-10-15
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzzc20261015a1"
down_revision = "zzzzb20261015a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("fk_produtos_produto_mestre", "produtos", type_="foreignkey")
    op.drop_column("produtos", "produto_mestre_id")

    op.drop_constraint(
        "fk_categorias_categoria_mestre", "categorias", type_="foreignkey"
    )
    op.drop_column("categorias", "categoria_mestre_id")

    op.drop_constraint("fk_marcas_marca_mestre", "marcas", type_="foreignkey")
    op.drop_column("marcas", "marca_mestre_id")

    op.drop_constraint(
        "fk_departamentos_departamento_mestre", "departamentos", type_="foreignkey"
    )
    op.drop_column("departamentos", "departamento_mestre_id")

    op.drop_table("produto_mestre")
    op.drop_table("categoria_mestre")
    op.drop_table("marca_mestre")
    op.drop_table("departamento_mestre")


def downgrade() -> None:
    # Remocao deliberada de feature sem uso (0 linhas em producao - mesmo
    # padrao ja usado em zzzy20261009a1). Recria so a estrutura; nao ha dado
    # a restaurar.
    for nome_tabela in ("categoria_mestre", "marca_mestre", "departamento_mestre"):
        op.create_table(
            nome_tabela,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "grupo_id",
                sa.Integer(),
                sa.ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
            sa.Column(
                "criado_em",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "atualizado_em",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "grupo_id", "nome", name=f"uq_{nome_tabela}_grupo_nome"
            ),
        )
        op.create_index(f"ix_{nome_tabela}_grupo_id", nome_tabela, ["grupo_id"])

    op.create_table(
        "produto_mestre",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "grupo_id",
            sa.Integer(),
            sa.ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("descricao_curta", sa.Text(), nullable=True),
        sa.Column("descricao_completa", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("imagem_principal", sa.String(length=255), nullable=True),
        sa.Column(
            "categoria_mestre_id",
            sa.Integer(),
            sa.ForeignKey("categoria_mestre.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "marca_mestre_id",
            sa.Integer(),
            sa.ForeignKey("marca_mestre.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "departamento_mestre_id",
            sa.Integer(),
            sa.ForeignKey("departamento_mestre.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ncm", sa.String(length=8), nullable=True),
        sa.Column("cest", sa.String(length=7), nullable=True),
        sa.Column("gtin_ean", sa.String(length=20), nullable=True),
        sa.Column("gtin_ean_tributario", sa.String(length=20), nullable=True),
        sa.Column("unidade", sa.String(length=10), nullable=True),
        sa.Column("peso_liquido", sa.Float(), nullable=True),
        sa.Column("peso_bruto", sa.Float(), nullable=True),
        sa.Column("largura", sa.Float(), nullable=True),
        sa.Column("altura", sa.Float(), nullable=True),
        sa.Column("profundidade", sa.Float(), nullable=True),
        sa.Column("itens_por_caixa", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("grupo_id", "nome", name="uq_produto_mestre_grupo_nome"),
    )
    op.create_index("ix_produto_mestre_grupo_id", "produto_mestre", ["grupo_id"])
    op.create_index("ix_produto_mestre_gtin_ean", "produto_mestre", ["gtin_ean"])

    op.add_column(
        "categorias",
        sa.Column("categoria_mestre_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_categorias_categoria_mestre",
        "categorias",
        "categoria_mestre",
        ["categoria_mestre_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("marcas", sa.Column("marca_mestre_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_marcas_marca_mestre",
        "marcas",
        "marca_mestre",
        ["marca_mestre_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "departamentos",
        sa.Column("departamento_mestre_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_departamentos_departamento_mestre",
        "departamentos",
        "departamento_mestre",
        ["departamento_mestre_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "produtos", sa.Column("produto_mestre_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_produtos_produto_mestre",
        "produtos",
        "produto_mestre",
        ["produto_mestre_id"],
        ["id"],
        ondelete="SET NULL",
    )
