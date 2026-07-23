"""add shared veterinary regulatory catalog

Revision ID: zwj20260723a1
Revises: zwi20260718a1
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


revision = "zwj20260723a1"
down_revision = "zwi20260718a1"
branch_labels = None
depends_on = None


MEDICATION_SOURCE_COLUMNS = (
    ("fonte", sa.String(length=50)),
    ("fonte_id", sa.String(length=120)),
    ("jurisdicao", sa.String(length=10)),
    ("status_regulatorio", sa.String(length=80)),
    ("bula_url", sa.String(length=1000)),
    ("pagina_fonte_url", sa.String(length=1000)),
    ("publicado_em", sa.Date()),
)


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("vet_produtos_regulatorios"):
        op.create_table(
            "vet_produtos_regulatorios",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("fonte", sa.String(length=50), nullable=False),
            sa.Column("fonte_id", sa.String(length=120), nullable=False),
            sa.Column("jurisdicao", sa.String(length=10), nullable=False),
            sa.Column("status_regulatorio", sa.String(length=80), nullable=True),
            sa.Column("tipo_documento", sa.String(length=80), nullable=True),
            sa.Column("nome", sa.String(length=500), nullable=False),
            sa.Column("nome_comercial", sa.String(length=255), nullable=True),
            sa.Column("principio_ativo", sa.Text(), nullable=True),
            sa.Column("fabricante", sa.String(length=255), nullable=True),
            sa.Column("forma_farmaceutica", sa.String(length=150), nullable=True),
            sa.Column("especies_indicadas", sa.JSON(), nullable=True),
            sa.Column("bula_url", sa.String(length=1000), nullable=False),
            sa.Column("pagina_fonte_url", sa.String(length=1000), nullable=True),
            sa.Column("publicado_em", sa.Date(), nullable=True),
            sa.Column(
                "atualizado_na_fonte_em", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column("metadados_fonte", sa.JSON(), nullable=True),
            sa.Column("conteudo_bula", sa.JSON(), nullable=True),
            sa.Column(
                "conteudo_hidratado_em", sa.DateTime(timezone=True), nullable=True
            ),
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
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "fonte",
                "fonte_id",
                name="uq_vet_produtos_regulatorios_fonte_id",
            ),
        )

    regulatory_indexes = _indexes("vet_produtos_regulatorios")
    for index_name, columns in (
        ("ix_vet_produtos_regulatorios_fonte", ["fonte"]),
        ("ix_vet_produtos_regulatorios_jurisdicao", ["jurisdicao"]),
        ("ix_vet_produtos_regulatorios_status_regulatorio", ["status_regulatorio"]),
        ("ix_vet_produtos_regulatorios_tipo_documento", ["tipo_documento"]),
        ("ix_vet_produtos_regulatorios_nome", ["nome"]),
        ("ix_vet_produtos_regulatorios_nome_comercial", ["nome_comercial"]),
        ("ix_vet_produtos_regulatorios_fabricante", ["fabricante"]),
        ("ix_vet_produtos_regulatorios_publicado_em", ["publicado_em"]),
        ("ix_vet_produtos_regulatorios_ativo", ["ativo"]),
        (
            "ix_vet_produtos_regulatorios_busca",
            ["nome", "principio_ativo", "fabricante"],
        ),
    ):
        if index_name not in regulatory_indexes:
            op.create_index(
                index_name,
                "vet_produtos_regulatorios",
                columns,
                unique=False,
            )

    medication_columns = _columns("vet_medicamentos_catalogo")
    for column_name, column_type in MEDICATION_SOURCE_COLUMNS:
        if column_name not in medication_columns:
            op.add_column(
                "vet_medicamentos_catalogo",
                sa.Column(column_name, column_type, nullable=True),
            )
    if "verificacao_status" not in medication_columns:
        op.add_column(
            "vet_medicamentos_catalogo",
            sa.Column(
                "verificacao_status",
                sa.String(length=30),
                nullable=False,
                server_default="nao_revisado",
            ),
        )

    medication_indexes = _indexes("vet_medicamentos_catalogo")
    for column_name in ("fonte", "fonte_id", "verificacao_status"):
        index_name = f"ix_vet_medicamentos_catalogo_{column_name}"
        if index_name not in medication_indexes:
            op.create_index(
                index_name,
                "vet_medicamentos_catalogo",
                [column_name],
                unique=False,
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("vet_medicamentos_catalogo"):
        medication_columns = _columns("vet_medicamentos_catalogo")
        medication_indexes = _indexes("vet_medicamentos_catalogo")
        for column_name in ("verificacao_status", "fonte_id", "fonte"):
            index_name = f"ix_vet_medicamentos_catalogo_{column_name}"
            if index_name in medication_indexes:
                op.drop_index(index_name, table_name="vet_medicamentos_catalogo")
        for column_name in (
            "verificacao_status",
            "publicado_em",
            "pagina_fonte_url",
            "bula_url",
            "status_regulatorio",
            "jurisdicao",
            "fonte_id",
            "fonte",
        ):
            if column_name in medication_columns:
                op.drop_column("vet_medicamentos_catalogo", column_name)

    if inspector.has_table("vet_produtos_regulatorios"):
        op.drop_table("vet_produtos_regulatorios")
