"""Produto mestre (+ categoria/marca/departamento mestre) — Checkpoint 2 da
camada geral do grupo comercial. Ver
Documentacao/Dominio/Plano-Camada-Geral.md. Puro schema, sem backfill —
vínculo é sempre ação explícita do usuário.

Revision ID: zzz20260918a1
Revises: zzy20260918a1
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "zzz20260918a1"
down_revision = "zzy20260918a1"
branch_labels = None
depends_on = None


def _criar_taxonomia_mestre(inspector, nome_tabela: str) -> None:
    if nome_tabela in set(inspector.get_table_names()):
        return
    op.create_table(
        nome_tabela,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("grupo_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["grupo_id"], ["grupos_comerciais.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "grupo_id", "nome", name=f"uq_{nome_tabela}_grupo_nome"
        ),
    )
    op.create_index(f"ix_{nome_tabela}_grupo_id", nome_tabela, ["grupo_id"])


def _adicionar_fk_mestre(
    inspector, tabela_local: str, coluna: str, tabela_mestre: str, nome_fk: str
) -> None:
    if tabela_local not in set(inspector.get_table_names()):
        return
    colunas = {c["name"] for c in inspector.get_columns(tabela_local)}
    if coluna in colunas:
        return
    op.add_column(tabela_local, sa.Column(coluna, sa.Integer(), nullable=True))
    op.create_foreign_key(
        nome_fk, tabela_local, tabela_mestre, [coluna], ["id"], ondelete="SET NULL"
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _criar_taxonomia_mestre(inspector, "categoria_mestre")
    _criar_taxonomia_mestre(inspector, "marca_mestre")
    _criar_taxonomia_mestre(inspector, "departamento_mestre")

    inspector = sa.inspect(bind)
    if "produto_mestre" not in set(inspector.get_table_names()):
        op.create_table(
            "produto_mestre",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("grupo_id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=200), nullable=False),
            sa.Column("descricao_curta", sa.Text(), nullable=True),
            sa.Column("descricao_completa", sa.Text(), nullable=True),
            sa.Column("tags", sa.Text(), nullable=True),
            sa.Column("imagem_principal", sa.String(length=255), nullable=True),
            sa.Column("categoria_mestre_id", sa.Integer(), nullable=True),
            sa.Column("marca_mestre_id", sa.Integer(), nullable=True),
            sa.Column("departamento_mestre_id", sa.Integer(), nullable=True),
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
            sa.ForeignKeyConstraint(
                ["grupo_id"], ["grupos_comerciais.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["categoria_mestre_id"], ["categoria_mestre.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["marca_mestre_id"], ["marca_mestre.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["departamento_mestre_id"],
                ["departamento_mestre.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("grupo_id", "nome", name="uq_produto_mestre_grupo_nome"),
        )
        op.create_index("ix_produto_mestre_grupo_id", "produto_mestre", ["grupo_id"])
        op.create_index("ix_produto_mestre_gtin_ean", "produto_mestre", ["gtin_ean"])

    inspector = sa.inspect(bind)
    _adicionar_fk_mestre(
        inspector, "categorias", "categoria_mestre_id", "categoria_mestre",
        "fk_categorias_categoria_mestre",
    )
    _adicionar_fk_mestre(
        inspector, "marcas", "marca_mestre_id", "marca_mestre", "fk_marcas_marca_mestre"
    )
    _adicionar_fk_mestre(
        inspector, "departamentos", "departamento_mestre_id", "departamento_mestre",
        "fk_departamentos_departamento_mestre",
    )
    _adicionar_fk_mestre(
        inspector, "produtos", "produto_mestre_id", "produto_mestre",
        "fk_produtos_produto_mestre",
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    for tabela_local, coluna, nome_fk in (
        ("produtos", "produto_mestre_id", "fk_produtos_produto_mestre"),
        ("departamentos", "departamento_mestre_id", "fk_departamentos_departamento_mestre"),
        ("marcas", "marca_mestre_id", "fk_marcas_marca_mestre"),
        ("categorias", "categoria_mestre_id", "fk_categorias_categoria_mestre"),
    ):
        if tabela_local in tabelas:
            colunas = {c["name"] for c in inspector.get_columns(tabela_local)}
            if coluna in colunas:
                with op.batch_alter_table(tabela_local) as batch_op:
                    batch_op.drop_constraint(nome_fk, type_="foreignkey")
                    batch_op.drop_column(coluna)

    for tabela in ("produto_mestre", "departamento_mestre", "marca_mestre", "categoria_mestre"):
        if tabela in sa.inspect(bind).get_table_names():
            op.drop_table(tabela)
