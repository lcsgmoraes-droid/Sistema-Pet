"""banho tosa calendario cliente

Revision ID: jj20260429a2
Revises: ji20260429a1
Create Date: 2026-04-29 22:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "jj20260429a2"
down_revision: Union[str, Sequence[str], None] = "ji20260429a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "banho_tosa_configuracoes",
        sa.Column(
            "mostrar_calendario_cliente",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "banho_tosa_configuracoes",
        sa.Column("whatsapp_agendamento", sa.String(length=30), nullable=True),
    )
    op.alter_column(
        "banho_tosa_configuracoes", "mostrar_calendario_cliente", server_default=None
    )


def downgrade() -> None:
    op.drop_column("banho_tosa_configuracoes", "whatsapp_agendamento")
    op.drop_column("banho_tosa_configuracoes", "mostrar_calendario_cliente")
