"""create the DRE channel detail table when it is missing

Revision ID: zwm20260813a1
Revises: zws20260807a1
Create Date: 2026-08-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zwm20260813a1"
down_revision = "zws20260807a1"
branch_labels = None
depends_on = None


TABLE_NAME = "dre_detalhe_canais"


def _missing_columns(inspector) -> set[str]:
    existing = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    expected = {
        "impostos",
        "impostos_detalhamento",
        "aliquota_efetiva_percent",
        "regime_tributario",
        "lucro_liquido",
        "margem_liquida_percent",
        "status",
        "score_saude",
        "origem",
        "origem_evento",
        "referencia_id",
        "observacao",
        "criado_em",
        "atualizado_em",
    }
    return expected - existing


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column(
                "id",
                sa.Integer(),
                sa.Identity(always=True),
                primary_key=True,
            ),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column("usuario_id", sa.Integer(), nullable=True),
            sa.Column("data_inicio", sa.Date(), nullable=False),
            sa.Column("data_fim", sa.Date(), nullable=False),
            sa.Column("mes", sa.Integer(), nullable=True),
            sa.Column("ano", sa.Integer(), nullable=True),
            sa.Column("canal", sa.String(length=50), nullable=False),
            sa.Column("receita_bruta", sa.Float(), server_default="0"),
            sa.Column("deducoes_receita", sa.Float(), server_default="0"),
            sa.Column("receita_liquida", sa.Float(), server_default="0"),
            sa.Column("custo_produtos_vendidos", sa.Float(), server_default="0"),
            sa.Column("lucro_bruto", sa.Float(), server_default="0"),
            sa.Column("margem_bruta_percent", sa.Float(), server_default="0"),
            sa.Column("despesas_vendas", sa.Float(), server_default="0"),
            sa.Column("despesas_pessoal", sa.Float(), server_default="0"),
            sa.Column("despesas_administrativas", sa.Float(), server_default="0"),
            sa.Column("despesas_financeiras", sa.Float(), server_default="0"),
            sa.Column("outras_despesas", sa.Float(), server_default="0"),
            sa.Column(
                "total_despesas_operacionais", sa.Float(), server_default="0"
            ),
            sa.Column("lucro_operacional", sa.Float(), server_default="0"),
            sa.Column(
                "margem_operacional_percent", sa.Float(), server_default="0"
            ),
            sa.Column("impostos", sa.Float(), server_default="0"),
            sa.Column("impostos_detalhamento", sa.Text(), nullable=True),
            sa.Column("aliquota_efetiva_percent", sa.Float(), server_default="0"),
            sa.Column("regime_tributario", sa.String(length=50), nullable=True),
            sa.Column("lucro_liquido", sa.Float(), server_default="0"),
            sa.Column("margem_liquida_percent", sa.Float(), server_default="0"),
            sa.Column("status", sa.String(length=50), nullable=True),
            sa.Column("score_saude", sa.Integer(), server_default="0"),
            sa.Column("origem", sa.String(length=50), nullable=True),
            sa.Column("origem_evento", sa.String(length=50), nullable=True),
            sa.Column("referencia_id", sa.String(length=100), nullable=True),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
    else:
        missing = _missing_columns(inspector)
        optional_columns = {
            "impostos": sa.Column("impostos", sa.Float(), server_default="0"),
            "impostos_detalhamento": sa.Column(
                "impostos_detalhamento", sa.Text(), nullable=True
            ),
            "aliquota_efetiva_percent": sa.Column(
                "aliquota_efetiva_percent", sa.Float(), server_default="0"
            ),
            "regime_tributario": sa.Column(
                "regime_tributario", sa.String(length=50), nullable=True
            ),
            "lucro_liquido": sa.Column(
                "lucro_liquido", sa.Float(), server_default="0"
            ),
            "margem_liquida_percent": sa.Column(
                "margem_liquida_percent", sa.Float(), server_default="0"
            ),
            "status": sa.Column("status", sa.String(length=50), nullable=True),
            "score_saude": sa.Column(
                "score_saude", sa.Integer(), server_default="0"
            ),
            "origem": sa.Column("origem", sa.String(length=50), nullable=True),
            "origem_evento": sa.Column(
                "origem_evento", sa.String(length=50), nullable=True
            ),
            "referencia_id": sa.Column(
                "referencia_id", sa.String(length=100), nullable=True
            ),
            "observacao": sa.Column("observacao", sa.Text(), nullable=True),
            "criado_em": sa.Column(
                "criado_em", sa.DateTime(), server_default=sa.func.now()
            ),
            "atualizado_em": sa.Column(
                "atualizado_em", sa.DateTime(), server_default=sa.func.now()
            ),
        }
        for column_name in sorted(missing):
            op.add_column(TABLE_NAME, optional_columns[column_name])

    inspector = sa.inspect(bind)
    inspected_indexes = inspector.get_indexes(TABLE_NAME)
    existing_indexes = {index["name"] for index in inspected_indexes}
    indexes = {
        "ix_dre_detalhe_canais_tenant_id": ["tenant_id"],
        "ix_dre_detalhe_canais_usuario_id": ["usuario_id"],
        "ix_dre_detalhe_canais_canal": ["canal"],
        "ix_dre_detalhe_canais_origem": ["origem"],
        "ix_dre_detalhe_canais_origem_evento": ["origem_evento"],
        "ix_dre_detalhe_canais_referencia_id": ["referencia_id"],
        "ix_dre_detalhe_canais_criado_em": ["criado_em"],
    }
    for index_name, columns in indexes.items():
        if index_name not in existing_indexes:
            op.create_index(index_name, TABLE_NAME, columns)

    unique_name = "uq_dre_detalhe_canais_periodo_canal"
    unique_columns = {"tenant_id", "data_inicio", "data_fim", "canal"}
    has_period_channel_unique = any(
        index.get("unique")
        and set(index.get("column_names") or []) == unique_columns
        for index in inspected_indexes
    )
    if unique_name not in existing_indexes and not has_period_channel_unique:
        op.create_index(
            unique_name,
            TABLE_NAME,
            ["tenant_id", "data_inicio", "data_fim", "canal"],
            unique=True,
        )

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(TABLE_NAME,),
        enable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(TABLE_NAME):
        return

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(TABLE_NAME,),
        enable=False,
    )
    op.drop_table(TABLE_NAME)
