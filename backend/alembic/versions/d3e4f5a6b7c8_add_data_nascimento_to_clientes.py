"""add_data_nascimento_to_clientes

Revision ID: d3e4f5a6b7c8
Revises: c1d2e3f4a5b6
Create Date: 2026-03-04

Adiciona campo data_nascimento (DateTime, nullable) à tabela clientes.
Necessário para campanhas de aniversário de cliente (BirthdayHandler).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'clientes',
        sa.Column('data_nascimento', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('clientes', 'data_nascimento')
