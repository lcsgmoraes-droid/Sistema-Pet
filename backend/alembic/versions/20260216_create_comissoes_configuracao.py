"""create_comissoes_configuracao

Revision ID: 20260216_comissoes_cfg
Revises: 20260216_tenant_fluxo
Create Date: 2026-02-16 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import NUMERIC


# revision identifiers, used by Alembic.
revision: str = '20260216_comissoes_cfg'
down_revision: Union[str, Sequence[str], None] = '20260216_tenant_fluxo'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create comissoes_configuracao table."""
    op.create_table(
        'comissoes_configuracao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('funcionario_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('referencia_id', sa.Integer(), nullable=False),
        sa.Column('percentual', NUMERIC, nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('tipo_calculo', sa.String(50), nullable=True, server_default='percentual'),
        sa.Column('desconta_taxa_cartao', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('desconta_impostos', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('desconta_custo_entrega', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('comissao_venda_parcial', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('percentual_loja', NUMERIC, nullable=True, server_default='0'),
        sa.Column('permite_edicao_venda', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_comissoes_configuracao_id', 'comissoes_configuracao', ['id'])
    op.create_index('ix_comissoes_configuracao_funcionario_id', 'comissoes_configuracao', ['funcionario_id'])
    
    # Create foreign key
    op.create_foreign_key(
        'fk_comissoes_configuracao_funcionario',
        'comissoes_configuracao', 'clientes',
        ['funcionario_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Drop comissoes_configuracao table."""
    op.drop_table('comissoes_configuracao')
