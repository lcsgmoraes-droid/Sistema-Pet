"""entrega_regra_acerto_entregador

Revision ID: 268eb76af817
Revises: e414f4e85016
Create Date: 2026-01-31 20:44:53.969091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '268eb76af817'
down_revision: Union[str, Sequence[str], None] = 'e414f4e85016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona campos de acerto financeiro para entregadores."""
    # Verificar se colunas já existem antes de adicionar
    from sqlalchemy import inspect
    from alembic import context
    
    conn = context.get_bind()
    inspector = inspect(conn)
    existing_columns = [c['name'] for c in inspector.get_columns('clientes')]
    
    if 'tipo_acerto_entrega' not in existing_columns:
        op.add_column(
            "clientes",
            sa.Column("tipo_acerto_entrega", sa.String(length=20), nullable=True)
        )

    if 'dia_semana_acerto' not in existing_columns:
        op.add_column(
            "clientes",
            sa.Column("dia_semana_acerto", sa.Integer(), nullable=True)
        )

    if 'dia_mes_acerto' not in existing_columns:
        op.add_column(
            "clientes",
            sa.Column("dia_mes_acerto", sa.Integer(), nullable=True)
        )

    if 'data_ultimo_acerto' not in existing_columns:
        op.add_column(
            "clientes",
            sa.Column("data_ultimo_acerto", sa.Date(), nullable=True)
        )


def downgrade() -> None:
    """Remove campos de acerto financeiro."""
    op.drop_column("clientes", "data_ultimo_acerto")
    op.drop_column("clientes", "dia_mes_acerto")
    op.drop_column("clientes", "dia_semana_acerto")
    op.drop_column("clientes", "tipo_acerto_entrega")
