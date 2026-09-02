"""configura encargos automáticos do crediário

Revision ID: zyt20260829a1
Revises: zys20260829a1
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa

revision = "zyt20260829a1"
down_revision = "zys20260829a1"
branch_labels = None
depends_on = None


def _colunas(tabela: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(tabela):
        return set()
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def upgrade() -> None:
    config_colunas = _colunas("empresa_config_geral")
    if "crediario_encargos_automaticos" not in config_colunas:
        op.add_column(
            "empresa_config_geral",
            sa.Column(
                "crediario_encargos_automaticos",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "crediario_multa_percentual" not in config_colunas:
        op.add_column(
            "empresa_config_geral",
            sa.Column(
                "crediario_multa_percentual",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="2.00",
            ),
        )
    if "crediario_juros_mensal_percentual" not in config_colunas:
        op.add_column(
            "empresa_config_geral",
            sa.Column(
                "crediario_juros_mensal_percentual",
                sa.Numeric(6, 3),
                nullable=False,
                server_default="1.000",
            ),
        )

    conta_colunas = _colunas("contas_receber")
    if "data_ultimo_calculo_encargos" not in conta_colunas:
        op.add_column(
            "contas_receber",
            sa.Column("data_ultimo_calculo_encargos", sa.Date(), nullable=True),
        )
    if "multa_atraso_aplicada" not in conta_colunas:
        op.add_column(
            "contas_receber",
            sa.Column(
                "multa_atraso_aplicada",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    conta_colunas = _colunas("contas_receber")
    if "multa_atraso_aplicada" in conta_colunas:
        op.drop_column("contas_receber", "multa_atraso_aplicada")
    if "data_ultimo_calculo_encargos" in conta_colunas:
        op.drop_column("contas_receber", "data_ultimo_calculo_encargos")

    config_colunas = _colunas("empresa_config_geral")
    if "crediario_juros_mensal_percentual" in config_colunas:
        op.drop_column("empresa_config_geral", "crediario_juros_mensal_percentual")
    if "crediario_multa_percentual" in config_colunas:
        op.drop_column("empresa_config_geral", "crediario_multa_percentual")
    if "crediario_encargos_automaticos" in config_colunas:
        op.drop_column("empresa_config_geral", "crediario_encargos_automaticos")
