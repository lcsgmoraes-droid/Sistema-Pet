"""add governed veterinary clinical evidence registry

Revision ID: zwk20260723a1
Revises: zwj20260723a1
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa

revision = "zwk20260723a1"
down_revision = "zwj20260723a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("vet_conhecimento_fontes"):
        op.create_table(
            "vet_conhecimento_fontes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("codigo", sa.String(length=50), nullable=False),
            sa.Column("nome", sa.String(length=255), nullable=False),
            sa.Column("tipo", sa.String(length=50), nullable=False),
            sa.Column("url_base", sa.String(length=1000), nullable=False),
            sa.Column("jurisdicao", sa.String(length=20), nullable=True),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("termos_url", sa.String(length=1000), nullable=True),
            sa.Column(
                "requer_revisao",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "ativo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "ultima_sincronizacao_em",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column("ultimo_status", sa.String(length=30), nullable=True),
            sa.Column("ultimo_erro", sa.String(length=500), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("codigo"),
        )
        op.create_index(
            "ix_vet_conhecimento_fontes_codigo",
            "vet_conhecimento_fontes",
            ["codigo"],
            unique=True,
        )
        op.create_index(
            "ix_vet_conhecimento_fontes_ativo",
            "vet_conhecimento_fontes",
            ["ativo"],
            unique=False,
        )

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("vet_conhecimento_documentos"):
        op.create_table(
            "vet_conhecimento_documentos",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("fonte_id", sa.Integer(), nullable=False),
            sa.Column("fonte_documento_id", sa.String(length=120), nullable=False),
            sa.Column("titulo", sa.Text(), nullable=False),
            sa.Column("resumo", sa.Text(), nullable=True),
            sa.Column("autores", sa.JSON(), nullable=True),
            sa.Column("periodico", sa.String(length=500), nullable=True),
            sa.Column("doi", sa.String(length=255), nullable=True),
            sa.Column("url", sa.String(length=1000), nullable=False),
            sa.Column("idioma", sa.String(length=30), nullable=True),
            sa.Column("publicado_em", sa.Date(), nullable=True),
            sa.Column("especies", sa.JSON(), nullable=True),
            sa.Column("temas", sa.JSON(), nullable=True),
            sa.Column(
                "status_revisao",
                sa.String(length=30),
                nullable=False,
                server_default="pendente",
            ),
            sa.Column("motivo_revisao", sa.Text(), nullable=True),
            sa.Column("revisado_por_id", sa.Integer(), nullable=True),
            sa.Column("revisado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("hash_conteudo", sa.String(length=64), nullable=False),
            sa.Column("metadados_fonte", sa.JSON(), nullable=True),
            sa.Column(
                "ativo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["fonte_id"],
                ["vet_conhecimento_fontes.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "fonte_id",
                "fonte_documento_id",
                name="uq_vet_conhecimento_documentos_fonte_documento",
            ),
        )
        for index_name, columns in (
            ("ix_vet_conhecimento_documentos_fonte_id", ["fonte_id"]),
            ("ix_vet_conhecimento_documentos_doi", ["doi"]),
            ("ix_vet_conhecimento_documentos_publicado_em", ["publicado_em"]),
            (
                "ix_vet_conhecimento_documentos_status_revisao",
                ["status_revisao"],
            ),
            ("ix_vet_conhecimento_documentos_ativo", ["ativo"]),
            (
                "ix_vet_conhecimento_documentos_retrieval",
                ["status_revisao", "ativo", "publicado_em"],
            ),
        ):
            op.create_index(
                index_name,
                "vet_conhecimento_documentos",
                columns,
                unique=False,
            )

    op.execute(
        sa.text("""
            INSERT INTO vet_conhecimento_fontes
                (codigo, nome, tipo, url_base, jurisdicao, descricao,
                 termos_url, requer_revisao, ativo)
            SELECT
                'pubmed',
                'PubMed / National Library of Medicine',
                'literatura_cientifica',
                'https://pubmed.ncbi.nlm.nih.gov/',
                'US',
                'Metadados bibliograficos e resumos cientificos. '
                'Ingestao nao equivale a validacao clinica.',
                'https://www.ncbi.nlm.nih.gov/home/develop/api/',
                true,
                true
            WHERE NOT EXISTS (
                SELECT 1
                FROM vet_conhecimento_fontes
                WHERE codigo = 'pubmed'
            )
            """)
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("vet_conhecimento_documentos"):
        op.drop_table("vet_conhecimento_documentos")
    if inspector.has_table("vet_conhecimento_fontes"):
        op.drop_table("vet_conhecimento_fontes")
