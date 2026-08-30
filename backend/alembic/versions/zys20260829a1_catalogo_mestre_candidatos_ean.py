"""adiciona fila privada de candidatos do catalogo mestre por EAN

Revision ID: zys20260829a1
Revises: zyr20260829a1
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa

revision = "zys20260829a1"
down_revision = "zyr20260829a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalogo_mestre_produto_candidatos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gtin", sa.String(length=14), nullable=False),
        sa.Column("nome_sugerido", sa.String(length=500), nullable=False),
        sa.Column("tipo_catalogo_sugerido", sa.String(length=30), nullable=True),
        sa.Column(
            "decisao_escopo_sugerida",
            sa.String(length=30),
            nullable=False,
            server_default="revisao_necessaria",
        ),
        sa.Column("motivo_sugestao", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=30), nullable=False, server_default="pendente"
        ),
        sa.Column("produto_mestre_id", sa.Integer(), nullable=True),
        sa.Column(
            "fonte_identidade_status",
            sa.String(length=40),
            nullable=False,
            server_default="nao_verificada",
        ),
        sa.Column("metadados", sa.JSON(), nullable=True),
        sa.Column("revisada_por_id", sa.Integer(), nullable=True),
        sa.Column("revisada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "decisao_escopo_sugerida IN "
            "('provavel_elegivel', 'provavel_fora_escopo', 'revisao_necessaria')",
            name="ck_cat_mestre_cand_escopo",
        ),
        sa.ForeignKeyConstraint(
            ["produto_mestre_id"],
            ["catalogo_mestre_produtos.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gtin", name="uq_cat_mestre_candidato_gtin"),
    )
    op.create_index(
        "ix_cat_mestre_cand_status",
        "catalogo_mestre_produto_candidatos",
        ["status", "decisao_escopo_sugerida"],
        unique=False,
    )
    op.create_index(
        "ix_cat_mestre_cand_tipo",
        "catalogo_mestre_produto_candidatos",
        ["tipo_catalogo_sugerido"],
        unique=False,
    )
    op.create_index(
        "ix_cat_mestre_cand_produto",
        "catalogo_mestre_produto_candidatos",
        ["produto_mestre_id"],
        unique=False,
    )

    op.create_table(
        "catalogo_mestre_candidato_evidencias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidato_id", sa.Integer(), nullable=False),
        sa.Column("source_ref", sa.String(length=300), nullable=False),
        sa.Column("fonte_relatorio", sa.String(length=100), nullable=True),
        sa.Column("nome_arquivo_original", sa.String(length=500), nullable=False),
        sa.Column("hash_arquivo", sa.String(length=64), nullable=False),
        sa.Column("staging_path", sa.String(length=1000), nullable=False),
        sa.Column("formato", sa.String(length=20), nullable=False),
        sa.Column("largura", sa.Integer(), nullable=True),
        sa.Column("altura", sa.Integer(), nullable=True),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "direitos_uso_status",
            sa.String(length=30),
            nullable=False,
            server_default="nao_verificado",
        ),
        sa.Column("metadados", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["candidato_id"],
            ["catalogo_mestre_produto_candidatos.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidato_id",
            "hash_arquivo",
            name="uq_cat_mestre_cand_evid_hash",
        ),
    )
    op.create_index(
        "ix_cat_mestre_cand_evid_candidato",
        "catalogo_mestre_candidato_evidencias",
        ["candidato_id"],
        unique=False,
    )
    op.create_index(
        "ix_cat_mestre_cand_evid_hash",
        "catalogo_mestre_candidato_evidencias",
        ["hash_arquivo"],
        unique=False,
    )
    op.create_index(
        "ix_cat_mestre_cand_evid_direitos",
        "catalogo_mestre_candidato_evidencias",
        ["direitos_uso_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("catalogo_mestre_candidato_evidencias")
    op.drop_table("catalogo_mestre_produto_candidatos")
