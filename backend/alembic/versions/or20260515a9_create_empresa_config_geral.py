"""create empresa config geral table

Revision ID: or20260515a9
Revises: oq20260515a8
Create Date: 2026-05-15 19:25:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "or20260515a9"
down_revision = "oq20260515a8"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _columns(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _create_index_if_missing(
    index_name: str, table_name: str, columns: list[str], *, unique: bool = False
) -> None:
    if index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, columns, unique=unique)


EMPRESA_CONFIG_GERAL_COLUMNS = {
    "tenant_id": sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
    "created_at": sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    ),
    "updated_at": sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    ),
    "razao_social": sa.Column("razao_social", sa.String(length=200), nullable=True),
    "nome_fantasia": sa.Column("nome_fantasia", sa.String(length=200), nullable=True),
    "cnpj": sa.Column("cnpj", sa.String(length=18), nullable=True),
    "inscricao_estadual": sa.Column(
        "inscricao_estadual", sa.String(length=20), nullable=True
    ),
    "inscricao_municipal": sa.Column(
        "inscricao_municipal", sa.String(length=20), nullable=True
    ),
    "logradouro": sa.Column("logradouro", sa.String(length=200), nullable=True),
    "numero": sa.Column("numero", sa.String(length=20), nullable=True),
    "complemento": sa.Column("complemento", sa.String(length=100), nullable=True),
    "bairro": sa.Column("bairro", sa.String(length=100), nullable=True),
    "cidade": sa.Column("cidade", sa.String(length=100), nullable=True),
    "uf": sa.Column("uf", sa.String(length=2), nullable=True),
    "cep": sa.Column("cep", sa.String(length=10), nullable=True),
    "telefone": sa.Column("telefone", sa.String(length=20), nullable=True),
    "email": sa.Column("email", sa.String(length=100), nullable=True),
    "site": sa.Column("site", sa.String(length=100), nullable=True),
    "margem_saudavel_minima": sa.Column(
        "margem_saudavel_minima",
        sa.Numeric(precision=5, scale=2),
        nullable=True,
        server_default="30.0",
    ),
    "margem_alerta_minima": sa.Column(
        "margem_alerta_minima",
        sa.Numeric(precision=5, scale=2),
        nullable=True,
        server_default="15.0",
    ),
    "mensagem_venda_saudavel": sa.Column(
        "mensagem_venda_saudavel", sa.Text(), nullable=True
    ),
    "mensagem_venda_alerta": sa.Column(
        "mensagem_venda_alerta", sa.Text(), nullable=True
    ),
    "mensagem_venda_critica": sa.Column(
        "mensagem_venda_critica", sa.Text(), nullable=True
    ),
    "dias_tolerancia_atraso": sa.Column(
        "dias_tolerancia_atraso", sa.Integer(), nullable=True, server_default="5"
    ),
    "meta_faturamento_mensal": sa.Column(
        "meta_faturamento_mensal",
        sa.Numeric(precision=12, scale=2),
        nullable=True,
        server_default="0",
    ),
    "alerta_estoque_percentual": sa.Column(
        "alerta_estoque_percentual", sa.Integer(), nullable=True, server_default="20"
    ),
    "dias_produto_parado": sa.Column(
        "dias_produto_parado", sa.Integer(), nullable=True, server_default="90"
    ),
    "aliquota_imposto_padrao": sa.Column(
        "aliquota_imposto_padrao",
        sa.Numeric(precision=5, scale=2),
        nullable=True,
        server_default="7.0",
    ),
    "ativo": sa.Column(
        "ativo", sa.Boolean(), nullable=True, server_default=sa.text("true")
    ),
}


def upgrade() -> None:
    inspector = _inspector()

    if not inspector.has_table("empresa_config_geral"):
        op.create_table(
            "empresa_config_geral",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            *EMPRESA_CONFIG_GERAL_COLUMNS.values(),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_empresa_config_geral_tenant_id",
            "empresa_config_geral",
            ["tenant_id"],
            unique=False,
        )
        return

    existing_columns = _columns("empresa_config_geral")
    for column_name, column in EMPRESA_CONFIG_GERAL_COLUMNS.items():
        if column_name not in existing_columns:
            op.add_column("empresa_config_geral", column)

    _create_index_if_missing(
        "ix_empresa_config_geral_tenant_id", "empresa_config_geral", ["tenant_id"]
    )


def downgrade() -> None:
    inspector = _inspector()
    if inspector.has_table("empresa_config_geral"):
        op.execute("DROP INDEX IF EXISTS ix_empresa_config_geral_tenant_id")
        op.drop_table("empresa_config_geral")
