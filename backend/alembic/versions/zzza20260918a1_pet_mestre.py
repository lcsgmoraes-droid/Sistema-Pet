"""Pet mestre — Checkpoint 3 da camada geral do grupo comercial. Puro
schema, sem backfill. Ver Documentacao/Dominio/Plano-Camada-Geral.md.

Revision ID: zzza20260918a1
Revises: zzz20260918a1
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "zzza20260918a1"
down_revision = "zzz20260918a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "pet_mestre" not in set(inspector.get_table_names()):
        op.create_table(
            "pet_mestre",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("grupo_id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=255), nullable=False),
            sa.Column("especie", sa.String(length=50), nullable=False),
            sa.Column("raca", sa.String(length=100), nullable=True),
            sa.Column("sexo", sa.String(length=10), nullable=True),
            sa.Column("porte", sa.String(length=20), nullable=True),
            sa.Column("cor", sa.String(length=100), nullable=True),
            sa.Column("cor_pelagem", sa.String(length=100), nullable=True),
            sa.Column("data_nascimento", sa.DateTime(), nullable=True),
            sa.Column("castrado", sa.Boolean(), nullable=True),
            sa.Column("castrado_data", sa.Date(), nullable=True),
            sa.Column("foto_url", sa.String(length=500), nullable=True),
            sa.Column("microchip", sa.String(length=50), nullable=True),
            sa.Column("tipo_sanguineo", sa.String(length=20), nullable=True),
            sa.Column("pedigree_registro", sa.String(length=100), nullable=True),
            sa.Column("alergias", sa.Text(), nullable=True),
            sa.Column("alergias_lista", sa.JSON(), nullable=True),
            sa.Column("doencas_cronicas", sa.Text(), nullable=True),
            sa.Column("condicoes_cronicas_lista", sa.JSON(), nullable=True),
            sa.Column("medicamentos_continuos", sa.Text(), nullable=True),
            sa.Column("medicamentos_continuos_lista", sa.JSON(), nullable=True),
            sa.Column("restricoes_alimentares_lista", sa.JSON(), nullable=True),
            sa.Column("historico_clinico", sa.Text(), nullable=True),
            sa.Column("temperamento", sa.String(length=50), nullable=True),
            sa.Column("reacao_animais", sa.String(length=50), nullable=True),
            sa.Column("reacao_pessoas", sa.String(length=50), nullable=True),
            sa.Column("medo_secador", sa.String(length=50), nullable=True),
            sa.Column("medo_tesoura", sa.String(length=50), nullable=True),
            sa.Column("aceita_focinheira", sa.String(length=50), nullable=True),
            sa.Column("comportamento_carro", sa.String(length=50), nullable=True),
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
        )
        op.create_index("ix_pet_mestre_grupo_id", "pet_mestre", ["grupo_id"])
        op.create_index("ix_pet_mestre_microchip", "pet_mestre", ["microchip"])

    inspector = sa.inspect(bind)
    if "pets" in set(inspector.get_table_names()):
        colunas = {c["name"] for c in inspector.get_columns("pets")}
        if "pet_mestre_id" not in colunas:
            op.add_column(
                "pets", sa.Column("pet_mestre_id", sa.Integer(), nullable=True)
            )
            op.create_foreign_key(
                "fk_pets_pet_mestre",
                "pets",
                "pet_mestre",
                ["pet_mestre_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "pets" in tabelas:
        colunas = {c["name"] for c in inspector.get_columns("pets")}
        if "pet_mestre_id" in colunas:
            with op.batch_alter_table("pets") as batch_op:
                batch_op.drop_constraint("fk_pets_pet_mestre", type_="foreignkey")
                batch_op.drop_column("pet_mestre_id")

    if "pet_mestre" in sa.inspect(bind).get_table_names():
        op.drop_table("pet_mestre")
