"""create company groups, monthly codes and invitations

Revision ID: zww20260822a1
Revises: zwv20260822a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zww20260822a1"
down_revision = "zwv20260822a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tabelas = set(sa.inspect(bind).get_table_names())

    if "empresa_grupos" not in tabelas:
        op.create_table(
            "empresa_grupos",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("nome", sa.String(length=150), nullable=False),
            sa.Column("criado_por_empresa_id", sa.String(length=36), nullable=False),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
            sa.Column(
                "status", sa.String(length=20), server_default="ativo", nullable=False
            ),
            sa.Column(
                "versao_membros", sa.Integer(), server_default="1", nullable=False
            ),
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
            sa.CheckConstraint(
                "status IN ('ativo', 'inativo')", name="ck_empresa_grupos_status"
            ),
            sa.ForeignKeyConstraint(
                ["criado_por_empresa_id"], ["tenants.id"], ondelete="RESTRICT"
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if "empresa_grupo_membros" not in tabelas:
        op.create_table(
            "empresa_grupo_membros",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("grupo_id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.String(length=36), nullable=False),
            sa.Column(
                "papel", sa.String(length=20), server_default="membro", nullable=False
            ),
            sa.Column(
                "status", sa.String(length=20), server_default="ativo", nullable=False
            ),
            sa.Column(
                "entrou_em",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("removido_em", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "papel IN ('responsavel', 'membro')",
                name="ck_empresa_grupo_membros_papel",
            ),
            sa.CheckConstraint(
                "status IN ('ativo', 'removido')",
                name="ck_empresa_grupo_membros_status",
            ),
            sa.ForeignKeyConstraint(
                ["empresa_id"], ["tenants.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["grupo_id"], ["empresa_grupos.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "grupo_id", "empresa_id", name="uq_empresa_grupo_membro_empresa"
            ),
        )
        op.create_index(
            "ix_empresa_grupo_membros_grupo_id", "empresa_grupo_membros", ["grupo_id"]
        )
        op.create_index(
            "ix_empresa_grupo_membros_empresa_status",
            "empresa_grupo_membros",
            ["empresa_id", "status"],
        )

    if "empresa_grupo_codigos" not in tabelas:
        op.create_table(
            "empresa_grupo_codigos",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("empresa_id", sa.String(length=36), nullable=False),
            sa.Column("competencia", sa.String(length=7), nullable=False),
            sa.Column("codigo", sa.String(length=12), nullable=False),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
            sa.Column(
                "criado_em",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["empresa_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("codigo", name="uq_empresa_grupo_codigos_codigo"),
            sa.UniqueConstraint(
                "empresa_id", "competencia", name="uq_empresa_grupo_codigo_competencia"
            ),
        )
        op.create_index(
            "ix_empresa_grupo_codigos_codigo", "empresa_grupo_codigos", ["codigo"]
        )
        op.create_index(
            "ix_empresa_grupo_codigos_empresa_validade",
            "empresa_grupo_codigos",
            ["empresa_id", "expira_em"],
        )

    if "empresa_grupo_convites" not in tabelas:
        op.create_table(
            "empresa_grupo_convites",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("grupo_id", sa.Integer(), nullable=False),
            sa.Column("empresa_convidada_id", sa.String(length=36), nullable=False),
            sa.Column("convidado_por_empresa_id", sa.String(length=36), nullable=False),
            sa.Column("convidado_por_usuario_id", sa.Integer(), nullable=False),
            sa.Column("respondido_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=20),
                server_default="pendente",
                nullable=False,
            ),
            sa.Column(
                "criado_em",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("respondido_em", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(
                "status IN ('pendente', 'aceito', 'recusado', 'expirado')",
                name="ck_empresa_grupo_convites_status",
            ),
            sa.ForeignKeyConstraint(
                ["convidado_por_empresa_id"], ["tenants.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["empresa_convidada_id"], ["tenants.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(
                ["grupo_id"], ["empresa_grupos.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "grupo_id",
                "empresa_convidada_id",
                name="uq_empresa_grupo_convite_empresa",
            ),
        )
        op.create_index(
            "ix_empresa_grupo_convites_grupo_id", "empresa_grupo_convites", ["grupo_id"]
        )
        op.create_index(
            "ix_empresa_grupo_convites_destino_status",
            "empresa_grupo_convites",
            ["empresa_convidada_id", "status", "expira_em"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tabelas = set(sa.inspect(bind).get_table_names())
    for tabela in (
        "empresa_grupo_convites",
        "empresa_grupo_codigos",
        "empresa_grupo_membros",
        "empresa_grupos",
    ):
        if tabela in tabelas:
            op.drop_table(tabela)
