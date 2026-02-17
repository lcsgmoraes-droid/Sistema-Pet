"""add conciliation fields to contas_receber

Revision ID: b1eaca5a7d14
Revises: 8e0c59d253f7
Create Date: 2026-01-31 13:36:43.966074

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1eaca5a7d14'
down_revision: Union[str, Sequence[str], None] = '8e0c59d253f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'contas_receber',
        sa.Column('nsu', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'contas_receber',
        sa.Column('adquirente', sa.String(length=50), nullable=True)
    )
    op.add_column(
        'contas_receber',
        sa.Column('conciliado', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column(
        'contas_receber',
        sa.Column('data_conciliacao', sa.Date(), nullable=True)
    )
    # data_recebimento já existe, não adicionar novamente
    # op.add_column(
    #     'contas_receber',
    #     sa.Column('data_recebimento', sa.Date(), nullable=True)
    # )


def downgrade() -> None:
    # op.drop_column('contas_receber', 'data_recebimento')
    op.drop_column('contas_receber', 'data_conciliacao')
    op.drop_column('contas_receber', 'conciliado')
    op.drop_column('contas_receber', 'adquirente')
    op.drop_column('contas_receber', 'nsu')
