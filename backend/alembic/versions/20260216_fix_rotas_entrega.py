"""add_missing_columns_to_rotas_entrega

Revision ID: 20260216_fix_rotas_entrega
Revises: 20260216_fix_config_entrega
Create Date: 2026-02-16 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import NUMERIC


# revision identifiers, used by Alembic.
revision: str = '20260216_fix_rotas_entrega'
down_revision: Union[str, Sequence[str], None] = '20260216_fix_config_entrega'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to rotas_entrega table."""
    
    # Add ponto_inicial_rota and ponto_final_rota
    op.add_column('rotas_entrega', sa.Column('ponto_inicial_rota', sa.Text(), nullable=True))
    op.add_column('rotas_entrega', sa.Column('ponto_final_rota', sa.Text(), nullable=True))
    op.add_column('rotas_entrega', sa.Column('retorna_origem', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    
    # Add custo fields
    op.add_column('rotas_entrega', sa.Column('custo_moto', NUMERIC(10, 2), nullable=True, server_default='0'))
    
    # Add repasse da taxa fields
    op.add_column('rotas_entrega', sa.Column('taxa_entrega_cliente', NUMERIC(10, 2), nullable=True))
    op.add_column('rotas_entrega', sa.Column('valor_repasse_entregador', NUMERIC(10, 2), nullable=True))
    
    # Add KM control fields
    op.add_column('rotas_entrega', sa.Column('km_inicial', NUMERIC(10, 2), nullable=True))
    op.add_column('rotas_entrega', sa.Column('km_final', NUMERIC(10, 2), nullable=True))
    
    # Add data_inicio and updated_at
    op.add_column('rotas_entrega', sa.Column('data_inicio', sa.DateTime(), nullable=True))
    op.add_column('rotas_entrega', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove added columns from rotas_entrega table."""
    op.drop_column('rotas_entrega', 'updated_at')
    op.drop_column('rotas_entrega', 'data_inicio')
    op.drop_column('rotas_entrega', 'km_final')
    op.drop_column('rotas_entrega', 'km_inicial')
    op.drop_column('rotas_entrega', 'valor_repasse_entregador')
    op.drop_column('rotas_entrega', 'taxa_entrega_cliente')
    op.drop_column('rotas_entrega', 'custo_moto')
    op.drop_column('rotas_entrega', 'retorna_origem')
    op.drop_column('rotas_entrega', 'ponto_final_rota')
    op.drop_column('rotas_entrega', 'ponto_inicial_rota')
