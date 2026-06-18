"""create empresa config fiscal table

Revision ID: on20260515a5
Revises: om20260515a4
Create Date: 2026-05-15 17:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "on20260515a5"
down_revision = "om20260515a4"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("empresa_config_fiscal"):
        op.create_table(
            "empresa_config_fiscal",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("fiscal_estado_padrao_id", sa.Integer(), nullable=True),
            sa.Column("uf", sa.String(length=2), nullable=False),
            sa.Column("regime_tributario", sa.String(length=50), nullable=False),
            sa.Column("cnae_principal", sa.String(length=10), nullable=True),
            sa.Column("contribuinte_icms", sa.Boolean(), nullable=False),
            sa.Column(
                "icms_aliquota_interna",
                sa.Numeric(precision=5, scale=2),
                nullable=False,
            ),
            sa.Column(
                "icms_aliquota_interestadual",
                sa.Numeric(precision=5, scale=2),
                nullable=False,
            ),
            sa.Column("aplica_difal", sa.Boolean(), nullable=False),
            sa.Column("cfop_venda_interna", sa.String(length=4), nullable=False),
            sa.Column("cfop_venda_interestadual", sa.String(length=4), nullable=False),
            sa.Column("cfop_compra", sa.String(length=4), nullable=False),
            sa.Column("pis_cst_padrao", sa.String(length=3), nullable=True),
            sa.Column("pis_aliquota", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column("cofins_cst_padrao", sa.String(length=3), nullable=True),
            sa.Column(
                "cofins_aliquota", sa.Numeric(precision=5, scale=2), nullable=True
            ),
            sa.Column("municipio_iss", sa.String(length=100), nullable=True),
            sa.Column("iss_aliquota", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column(
                "iss_retido",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=True,
            ),
            sa.Column(
                "herdado_do_estado",
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=False,
            ),
            sa.Column(
                "simples_ativo",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=True,
            ),
            sa.Column(
                "simples_anexo", sa.String(length=5), server_default="I", nullable=True
            ),
            sa.Column(
                "aliquota_simples_vigente",
                sa.Numeric(precision=5, scale=2),
                server_default="0",
                nullable=True,
            ),
            sa.Column(
                "aliquota_simples_sugerida",
                sa.Numeric(precision=5, scale=2),
                server_default="0",
                nullable=True,
            ),
            sa.Column(
                "folha_valor_base_mensal",
                sa.Numeric(precision=10, scale=2),
                server_default="0",
                nullable=True,
            ),
            sa.Column(
                "inss_patronal_percentual",
                sa.Numeric(precision=5, scale=2),
                server_default="20",
                nullable=True,
            ),
            sa.Column(
                "fgts_percentual",
                sa.Numeric(precision=5, scale=2),
                server_default="8",
                nullable=True,
            ),
            sa.Column("cnae_descricao", sa.Text(), nullable=True),
            sa.Column(
                "cnaes_secundarios",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_empresa_config_fiscal_tenant_id",
            "empresa_config_fiscal",
            ["tenant_id"],
            unique=False,
        )
        return

    columns = _column_names(inspector, "empresa_config_fiscal")
    optional_columns = {
        "fiscal_estado_padrao_id": sa.Column(
            "fiscal_estado_padrao_id", sa.Integer(), nullable=True
        ),
        "cnae_principal": sa.Column(
            "cnae_principal", sa.String(length=10), nullable=True
        ),
        "pis_cst_padrao": sa.Column(
            "pis_cst_padrao", sa.String(length=3), nullable=True
        ),
        "pis_aliquota": sa.Column(
            "pis_aliquota", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        "cofins_cst_padrao": sa.Column(
            "cofins_cst_padrao", sa.String(length=3), nullable=True
        ),
        "cofins_aliquota": sa.Column(
            "cofins_aliquota", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        "municipio_iss": sa.Column(
            "municipio_iss", sa.String(length=100), nullable=True
        ),
        "iss_aliquota": sa.Column(
            "iss_aliquota", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        "iss_retido": sa.Column(
            "iss_retido", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        "simples_ativo": sa.Column(
            "simples_ativo",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
        "simples_anexo": sa.Column(
            "simples_anexo", sa.String(length=5), server_default="I", nullable=True
        ),
        "aliquota_simples_vigente": sa.Column(
            "aliquota_simples_vigente",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
            nullable=True,
        ),
        "aliquota_simples_sugerida": sa.Column(
            "aliquota_simples_sugerida",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
            nullable=True,
        ),
        "folha_valor_base_mensal": sa.Column(
            "folha_valor_base_mensal",
            sa.Numeric(precision=10, scale=2),
            server_default="0",
            nullable=True,
        ),
        "inss_patronal_percentual": sa.Column(
            "inss_patronal_percentual",
            sa.Numeric(precision=5, scale=2),
            server_default="20",
            nullable=True,
        ),
        "fgts_percentual": sa.Column(
            "fgts_percentual",
            sa.Numeric(precision=5, scale=2),
            server_default="8",
            nullable=True,
        ),
        "cnae_descricao": sa.Column("cnae_descricao", sa.Text(), nullable=True),
        "cnaes_secundarios": sa.Column(
            "cnaes_secundarios", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    }
    for column_name, column in optional_columns.items():
        if column_name not in columns:
            op.add_column("empresa_config_fiscal", column)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_empresa_config_fiscal_tenant_id ON empresa_config_fiscal (tenant_id)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("empresa_config_fiscal"):
        op.execute("DROP INDEX IF EXISTS ix_empresa_config_fiscal_tenant_id")
        op.drop_table("empresa_config_fiscal")
