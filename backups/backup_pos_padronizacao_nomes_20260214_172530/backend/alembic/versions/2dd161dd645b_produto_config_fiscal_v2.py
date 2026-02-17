"""produto_config_fiscal_v2

Revision ID: 2dd161dd645b
Revises: f1869ac8ce17
Create Date: 2026-01-30 23:46:36.858600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2dd161dd645b'
down_revision: Union[str, Sequence[str], None] = 'f1869ac8ce17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Criar tabela produto_config_fiscal."""
    
    op.create_table(
        'produto_config_fiscal',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('produto_id', sa.Integer(), nullable=False),
        
        # Controle de herança
        sa.Column('herdado_da_empresa', sa.Boolean(), nullable=False, server_default='true'),
        
        # Identificação fiscal
        sa.Column('ncm', sa.String(10), nullable=True),
        sa.Column('cest', sa.String(10), nullable=True),
        sa.Column('origem_mercadoria', sa.String(1), nullable=True),
        
        # ICMS
        sa.Column('cst_icms', sa.String(3), nullable=True),
        sa.Column('icms_aliquota', sa.Numeric(5, 2), nullable=True),
        sa.Column('icms_st', sa.Boolean(), nullable=True),
        
        # CFOP
        sa.Column('cfop_venda', sa.String(4), nullable=True),
        sa.Column('cfop_compra', sa.String(4), nullable=True),
        
        # PIS / COFINS
        sa.Column('pis_cst', sa.String(3), nullable=True),
        sa.Column('pis_aliquota', sa.Numeric(5, 2), nullable=True),
        sa.Column('cofins_cst', sa.String(3), nullable=True),
        sa.Column('cofins_aliquota', sa.Numeric(5, 2), nullable=True),
        
        sa.Column('observacao_fiscal', sa.Text(), nullable=True),
        
        # Auditoria
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'produto_id', name='uq_produto_config_fiscal_tenant_produto')
    )
    
    # Índices
    op.create_index('ix_produto_config_fiscal_tenant_id', 'produto_config_fiscal', ['tenant_id'])
    op.create_index('ix_produto_config_fiscal_produto_id', 'produto_config_fiscal', ['produto_id'])


def downgrade() -> None:
    """Remover tabela produto_config_fiscal."""
    
    op.drop_index('ix_produto_config_fiscal_produto_id', table_name='produto_config_fiscal')
    op.drop_index('ix_produto_config_fiscal_tenant_id', table_name='produto_config_fiscal')
    op.drop_table('produto_config_fiscal')
