"""add_periodicidade_acerto_entregador

Revision ID: 8422585f3dec
Revises: 08846c42f5cb
Create Date: 2026-02-09 00:26:12.570646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8422585f3dec'
down_revision: Union[str, Sequence[str], None] = '08846c42f5cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adiciona campo de periodicidade de acerto no cadastro do entregador
    # Este campo define quantos dias após a entrega o entregador deve receber o pagamento
    # Exemplo: 7 = pagamento semanal, 15 = quinzenal, 30 = mensal
    op.add_column('users', sa.Column('periodicidade_acerto_dias', sa.Integer(), nullable=True, server_default='7'))
    
    # Atualiza entregadores existentes para 7 dias (padrão semanal)
    op.execute("UPDATE users SET periodicidade_acerto_dias = 7 WHERE custo_operacional_tipo IS NOT NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'periodicidade_acerto_dias')
