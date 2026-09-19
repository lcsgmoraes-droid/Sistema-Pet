"""Pessoa mestre — Checkpoint 4 da camada geral do grupo comercial. Puro
schema, sem backfill (vínculo é sempre sugestão + confirmação manual, nunca
inferido em massa). Ver Documentacao/Dominio/Plano-Camada-Geral.md.

Revision ID: zzzb20260918a1
Revises: zzza20260918a1
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "zzzb20260918a1"
down_revision = "zzza20260918a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "pessoa_mestre" not in set(inspector.get_table_names()):
        op.create_table(
            "pessoa_mestre",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("grupo_id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=255), nullable=False),
            sa.Column("tipo_pessoa", sa.String(length=2), nullable=True),
            sa.Column("tipo_cadastro", sa.String(length=50), nullable=True),
            sa.Column("cpf", sa.String(length=14), nullable=True),
            sa.Column("cnpj", sa.String(length=18), nullable=True),
            sa.Column("inscricao_estadual", sa.String(length=20), nullable=True),
            sa.Column("razao_social", sa.String(length=255), nullable=True),
            sa.Column("nome_fantasia", sa.String(length=255), nullable=True),
            sa.Column("crmv", sa.String(length=20), nullable=True),
            sa.Column("data_nascimento", sa.DateTime(), nullable=True),
            sa.Column("telefone", sa.String(length=50), nullable=True),
            sa.Column("celular", sa.String(length=50), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("cep", sa.String(length=10), nullable=True),
            sa.Column("endereco", sa.String(length=500), nullable=True),
            sa.Column("numero", sa.String(length=20), nullable=True),
            sa.Column("complemento", sa.String(length=100), nullable=True),
            sa.Column("bairro", sa.String(length=100), nullable=True),
            sa.Column("cidade", sa.String(length=100), nullable=True),
            sa.Column("estado", sa.String(length=2), nullable=True),
            sa.Column("codigo_municipio", sa.String(length=7), nullable=True),
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
                "grupo_id", "cpf", name="uq_pessoa_mestre_grupo_cpf"
            ),
            sa.UniqueConstraint(
                "grupo_id", "cnpj", name="uq_pessoa_mestre_grupo_cnpj"
            ),
        )
        op.create_index("ix_pessoa_mestre_grupo_id", "pessoa_mestre", ["grupo_id"])
        op.create_index("ix_pessoa_mestre_cpf", "pessoa_mestre", ["cpf"])
        op.create_index("ix_pessoa_mestre_cnpj", "pessoa_mestre", ["cnpj"])

    inspector = sa.inspect(bind)
    if "clientes" in set(inspector.get_table_names()):
        colunas = {c["name"] for c in inspector.get_columns("clientes")}
        if "pessoa_mestre_id" not in colunas:
            op.add_column(
                "clientes", sa.Column("pessoa_mestre_id", sa.Integer(), nullable=True)
            )
            op.create_foreign_key(
                "fk_clientes_pessoa_mestre",
                "clientes",
                "pessoa_mestre",
                ["pessoa_mestre_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "clientes" in tabelas:
        colunas = {c["name"] for c in inspector.get_columns("clientes")}
        if "pessoa_mestre_id" in colunas:
            with op.batch_alter_table("clientes") as batch_op:
                batch_op.drop_constraint(
                    "fk_clientes_pessoa_mestre", type_="foreignkey"
                )
                batch_op.drop_column("pessoa_mestre_id")

    if "pessoa_mestre" in sa.inspect(bind).get_table_names():
        op.drop_table("pessoa_mestre")
