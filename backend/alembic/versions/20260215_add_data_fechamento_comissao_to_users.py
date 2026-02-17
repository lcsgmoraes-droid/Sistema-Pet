"""add_data_fechamento_comissao_to_users

Revision ID: 20260215_add_data_fechamento_comissao
Revises: 0d8fd366fe11
Create Date: 2026-02-15 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260215_add_data_fechamento_comissao'
down_revision: Union[str, Sequence[str], None] = '0d8fd366fe11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add data_fechamento_comissao column to users table"""
    # Adiciona coluna data_fechamento_comissao na tabela users
    op.add_column('users', sa.Column('data_fechamento_comissao', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove data_fechamento_comissao column from users table"""
    op.drop_column('users', 'data_fechamento_comissao')
