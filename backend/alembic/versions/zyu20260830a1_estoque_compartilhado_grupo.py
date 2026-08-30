"""add selective shared stock between group companies

Revision ID: zyu20260830a1
Revises: zyt20260829a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zyu20260830a1"
down_revision = "zyt20260829a1"
branch_labels = None
depends_on = None


def _tenant_id_type(inspector: sa.Inspector) -> sa.types.TypeEngine:
    for coluna in inspector.get_columns("tenants"):
        if coluna["name"] == "id":
            return coluna["type"].copy()
    raise RuntimeError("Coluna tenants.id nao encontrada")


def _criar_politica_leitura_produtos_compartilhados() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP POLICY IF EXISTS produtos_grupo_estoque_select ON produtos")
    op.execute(
        """
        CREATE POLICY produtos_grupo_estoque_select ON produtos
        FOR SELECT USING (
            EXISTS (
                SELECT 1
                FROM empresa_grupo_estoques_compartilhados egec
                JOIN empresa_grupos eg
                  ON eg.id = egec.grupo_id
                 AND eg.status = 'ativo'
                JOIN empresa_grupo_membros egmo
                  ON egmo.grupo_id = egec.grupo_id
                 AND egmo.empresa_id::text = egec.empresa_origem_id::text
                 AND egmo.status = 'ativo'
                JOIN empresa_grupo_membros egmc
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
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())
    tenant_id_type = _tenant_id_type(inspector)

    if "empresa_grupo_estoques_compartilhados" not in tabelas:
        op.create_table(
            "empresa_grupo_estoques_compartilhados",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("grupo_id", sa.Integer(), nullable=False),
            sa.Column("empresa_origem_id", tenant_id_type.copy(), nullable=False),
            sa.Column("produto_origem_id", sa.Integer(), nullable=False),
            sa.Column("empresa_consumidora_id", tenant_id_type.copy(), nullable=False),
            sa.Column(
                "status", sa.String(length=20), server_default="ativo", nullable=False
            ),
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
            sa.Column("removido_em", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "empresa_origem_id <> empresa_consumidora_id",
                name="ck_empresa_grupo_estoque_empresas_distintas",
            ),
            sa.CheckConstraint(
                "status IN ('ativo', 'removido')",
                name="ck_empresa_grupo_estoque_status",
            ),
            sa.ForeignKeyConstraint(
                ["grupo_id"], ["empresa_grupos.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["empresa_origem_id"], ["tenants.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["produto_origem_id"], ["produtos.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["empresa_consumidora_id"], ["tenants.id"], ondelete="RESTRICT"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "grupo_id",
                "empresa_origem_id",
                "produto_origem_id",
                "empresa_consumidora_id",
                name="uq_empresa_grupo_estoque_compartilhado",
            ),
        )
        op.create_index(
            "ix_empresa_grupo_estoque_compartilhado_consumidora_status",
            "empresa_grupo_estoques_compartilhados",
            ["empresa_consumidora_id", "status"],
        )
        op.create_index(
            "ix_empresa_grupo_estoque_compartilhado_origem_status",
            "empresa_grupo_estoques_compartilhados",
            ["empresa_origem_id", "status"],
        )

    inspector = sa.inspect(bind)
    colunas_item = {coluna["name"] for coluna in inspector.get_columns("venda_itens")}
    with op.batch_alter_table("venda_itens") as batch_op:
        if "estoque_origem_tenant_id" not in colunas_item:
            batch_op.add_column(
                sa.Column(
                    "estoque_origem_tenant_id", tenant_id_type.copy(), nullable=True
                )
            )
            batch_op.create_foreign_key(
                "fk_venda_itens_estoque_origem_tenant",
                "tenants",
                ["estoque_origem_tenant_id"],
                ["id"],
                ondelete="RESTRICT",
            )
        if "estoque_compartilhado_id" not in colunas_item:
            batch_op.add_column(
                sa.Column("estoque_compartilhado_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_venda_itens_estoque_compartilhado",
                "empresa_grupo_estoques_compartilhados",
                ["estoque_compartilhado_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "estoque_origem_nome" not in colunas_item:
            batch_op.add_column(
                sa.Column("estoque_origem_nome", sa.String(length=150), nullable=True)
            )

    _criar_politica_leitura_produtos_compartilhados()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS produtos_grupo_estoque_select ON produtos")

    inspector = sa.inspect(bind)
    if "venda_itens" in inspector.get_table_names():
        colunas_item = {
            coluna["name"] for coluna in inspector.get_columns("venda_itens")
        }
        with op.batch_alter_table("venda_itens") as batch_op:
            if "estoque_origem_nome" in colunas_item:
                batch_op.drop_column("estoque_origem_nome")
            if "estoque_compartilhado_id" in colunas_item:
                batch_op.drop_column("estoque_compartilhado_id")
            if "estoque_origem_tenant_id" in colunas_item:
                batch_op.drop_column("estoque_origem_tenant_id")

    if "empresa_grupo_estoques_compartilhados" in sa.inspect(bind).get_table_names():
        op.drop_table("empresa_grupo_estoques_compartilhados")
