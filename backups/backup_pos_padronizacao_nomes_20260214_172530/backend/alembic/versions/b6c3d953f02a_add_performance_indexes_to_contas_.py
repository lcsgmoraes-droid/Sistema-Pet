"""add performance indexes to contas_receber for conciliacao

Revision ID: b6c3d953f02a
Revises: b1eaca5a7d14
Create Date: 2026-01-31 13:57:41.286053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c3d953f02a'
down_revision: Union[str, Sequence[str], None] = 'b1eaca5a7d14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adiciona índices de performance para conciliação de cartão.
    
    Índices compostos para otimizar:
    - Busca de conta por NSU + tenant
    - Listagem de contas não conciliadas
    - Filtragem por adquirente
    """
    # Índice composto para busca por NSU (usado na conciliação)
    op.create_index(
        'idx_contas_receber_tenant_nsu',
        'contas_receber',
        ['tenant_id', 'nsu'],
        unique=False
    )
    
    # Índice composto para busca de contas não conciliadas (usado na listagem)
    op.create_index(
        'idx_contas_receber_conciliado',
        'contas_receber',
        ['tenant_id', 'conciliado'],
        unique=False
    )
    
    # Índice composto para filtragem por adquirente
    op.create_index(
        'idx_contas_receber_adquirente',
        'contas_receber',
        ['tenant_id', 'adquirente'],
        unique=False
    )


def downgrade() -> None:
    """Remove índices de performance."""
    op.drop_index('idx_contas_receber_adquirente', table_name='contas_receber')
    op.drop_index('idx_contas_receber_conciliado', table_name='contas_receber')
    op.drop_index('idx_contas_receber_tenant_nsu', table_name='contas_receber')
