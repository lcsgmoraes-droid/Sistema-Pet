"""banho tosa fluxo tempos precos

Revision ID: ji20260429a1
Revises: hi20260429a1
Create Date: 2026-04-29 20:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "ji20260429a1"
down_revision: Union[str, Sequence[str], None] = "hi20260429a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "banho_tosa_configuracoes", sa.Column("fluxo_etapas", sa.JSON(), nullable=True)
    )

    op.add_column(
        "banho_tosa_servicos",
        sa.Column("preco_base", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )

    op.add_column(
        "banho_tosa_parametros_porte",
        sa.Column(
            "multiplicador_pelo_curto",
            sa.Numeric(8, 4),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "banho_tosa_parametros_porte",
        sa.Column(
            "multiplicador_pelo_longo",
            sa.Numeric(8, 4),
            nullable=False,
            server_default="1.2",
        ),
    )
    op.add_column(
        "banho_tosa_parametros_porte",
        sa.Column(
            "tempo_extra_pelo_longo_min",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.add_column(
        "banho_tosa_etapas", sa.Column("ordem_fluxo", sa.Integer(), nullable=True)
    )
    op.add_column(
        "banho_tosa_etapas",
        sa.Column("tempo_previsto_minutos", sa.Integer(), nullable=True),
    )
    op.add_column(
        "banho_tosa_etapas", sa.Column("duracao_segundos", sa.Integer(), nullable=True)
    )

    op.alter_column("banho_tosa_servicos", "preco_base", server_default=None)
    op.alter_column(
        "banho_tosa_parametros_porte", "multiplicador_pelo_curto", server_default=None
    )
    op.alter_column(
        "banho_tosa_parametros_porte", "multiplicador_pelo_longo", server_default=None
    )
    op.alter_column(
        "banho_tosa_parametros_porte", "tempo_extra_pelo_longo_min", server_default=None
    )

    op.execute(
        """
        UPDATE banho_tosa_configuracoes
        SET fluxo_etapas = '["chegou", "banho", "secagem", "tosa", "pronto"]'::json
        WHERE fluxo_etapas IS NULL
        """
    )
    op.execute(
        """
        UPDATE banho_tosa_servicos
        SET preco_base = CASE lower(nome)
            WHEN 'banho higienico' THEN 85.00
            WHEN 'banho completo' THEN 120.00
            WHEN 'banho + tosa higienica' THEN 145.00
            WHEN 'tosa na maquina' THEN 110.00
            WHEN 'tosa completa' THEN 180.00
            WHEN 'desembaraco' THEN 45.00
            WHEN 'corte de unhas' THEN 25.00
            WHEN 'hidratacao de pelagem' THEN 40.00
            ELSE preco_base
        END
        WHERE preco_base = 0
        """
    )


def downgrade() -> None:
    op.drop_column("banho_tosa_etapas", "duracao_segundos")
    op.drop_column("banho_tosa_etapas", "tempo_previsto_minutos")
    op.drop_column("banho_tosa_etapas", "ordem_fluxo")
    op.drop_column("banho_tosa_parametros_porte", "tempo_extra_pelo_longo_min")
    op.drop_column("banho_tosa_parametros_porte", "multiplicador_pelo_longo")
    op.drop_column("banho_tosa_parametros_porte", "multiplicador_pelo_curto")
    op.drop_column("banho_tosa_servicos", "preco_base")
    op.drop_column("banho_tosa_configuracoes", "fluxo_etapas")
