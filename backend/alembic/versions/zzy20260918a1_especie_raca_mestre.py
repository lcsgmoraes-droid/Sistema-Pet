"""Espécie/Raça mestre — Checkpoint 1 da camada geral do grupo comercial.

Cria `especie_mestre`/`raca_mestre` (dado de taxonomia compartilhado entre
lojas do mesmo grupo comercial) e as colunas de vínculo opcional em
`especies`/`racas`. Puro schema — nenhum dado é migrado/inferido aqui (ver
Documentacao/Dominio/Plano-Camada-Geral.md: vínculo é sempre uma ação
explícita do usuário, nunca automático, então não há nada pra backfillar).

Revision ID: zzy20260918a1
Revises: zzx20260918a1
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "zzy20260918a1"
down_revision = "zzx20260918a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "especie_mestre" not in tabelas:
        op.create_table(
            "especie_mestre",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("grupo_id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column(
                "ativo", sa.Boolean(), server_default=sa.true(), nullable=False
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
            sa.ForeignKeyConstraint(
                ["grupo_id"], ["grupos_comerciais.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "grupo_id", "nome", name="uq_especie_mestre_grupo_nome"
            ),
        )
        op.create_index(
            "ix_especie_mestre_grupo_id", "especie_mestre", ["grupo_id"]
        )

    if "raca_mestre" not in tabelas:
        op.create_table(
            "raca_mestre",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("grupo_id", sa.Integer(), nullable=False),
            sa.Column("especie_mestre_id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column(
                "ativo", sa.Boolean(), server_default=sa.true(), nullable=False
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
            sa.ForeignKeyConstraint(
                ["grupo_id"], ["grupos_comerciais.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["especie_mestre_id"], ["especie_mestre.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "especie_mestre_id", "nome", name="uq_raca_mestre_especie_nome"
            ),
        )
        op.create_index("ix_raca_mestre_grupo_id", "raca_mestre", ["grupo_id"])
        op.create_index(
            "ix_raca_mestre_especie_mestre_id", "raca_mestre", ["especie_mestre_id"]
        )

    if "especies" in tabelas:
        colunas_especies = {c["name"] for c in inspector.get_columns("especies")}
        if "especie_mestre_id" not in colunas_especies:
            op.add_column(
                "especies",
                sa.Column("especie_mestre_id", sa.Integer(), nullable=True),
            )
            op.create_foreign_key(
                "fk_especies_especie_mestre",
                "especies",
                "especie_mestre",
                ["especie_mestre_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "racas" in tabelas:
        colunas_racas = {c["name"] for c in inspector.get_columns("racas")}
        if "raca_mestre_id" not in colunas_racas:
            op.add_column(
                "racas", sa.Column("raca_mestre_id", sa.Integer(), nullable=True)
            )
            op.create_foreign_key(
                "fk_racas_raca_mestre",
                "racas",
                "raca_mestre",
                ["raca_mestre_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "racas" in tabelas:
        colunas_racas = {c["name"] for c in inspector.get_columns("racas")}
        if "raca_mestre_id" in colunas_racas:
            with op.batch_alter_table("racas") as batch_op:
                batch_op.drop_constraint("fk_racas_raca_mestre", type_="foreignkey")
                batch_op.drop_column("raca_mestre_id")

    if "especies" in tabelas:
        colunas_especies = {c["name"] for c in inspector.get_columns("especies")}
        if "especie_mestre_id" in colunas_especies:
            with op.batch_alter_table("especies") as batch_op:
                batch_op.drop_constraint(
                    "fk_especies_especie_mestre", type_="foreignkey"
                )
                batch_op.drop_column("especie_mestre_id")

    if "raca_mestre" in tabelas:
        op.drop_table("raca_mestre")
    if "especie_mestre" in tabelas:
        op.drop_table("especie_mestre")
