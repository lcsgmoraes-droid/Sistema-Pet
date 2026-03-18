"""Add status field to estoque_movimentacoes for tracking reserved vs confirmed stock

Revision ID: 31142854c9e6
Revises: dep001cat2026
Create Date: 2026-03-18 08:01:16.473352

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '31142854c9e6'
down_revision: Union[str, Sequence[str], None] = 'dep001cat2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table('estoque_movimentacoes'):
        return

    colunas = {coluna['name'] for coluna in inspector.get_columns('estoque_movimentacoes')}
    if 'status' in colunas:
        return

    op.add_column(
        'estoque_movimentacoes',
        sa.Column('status', sa.String(length=20), server_default='confirmado', nullable=False),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table('estoque_movimentacoes'):
        return

    colunas = {coluna['name'] for coluna in inspector.get_columns('estoque_movimentacoes')}
    if 'status' in colunas:
        op.drop_column('estoque_movimentacoes', 'status')
