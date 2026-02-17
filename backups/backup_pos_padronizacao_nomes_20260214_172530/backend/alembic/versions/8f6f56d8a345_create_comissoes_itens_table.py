"""create_comissoes_itens_table

Revision ID: 8f6f56d8a345
Revises: 20260129_tornar_dre_obrigatorio
Create Date: 2026-01-29 20:59:50.810476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f6f56d8a345'
down_revision: Union[str, Sequence[str], None] = '20260129_tornar_dre_obrigatorio'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'comissoes_itens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('venda_id', sa.Integer(), nullable=False),
        sa.Column('venda_item_id', sa.Integer(), nullable=True),
        sa.Column('funcionario_id', sa.Integer(), nullable=False),
        sa.Column('produto_id', sa.Integer(), nullable=True),
        sa.Column('categoria_id', sa.Integer(), nullable=True),
        sa.Column('subcategoria_id', sa.Integer(), nullable=True),
        sa.Column('data_venda', sa.Date(), nullable=False),
        sa.Column('quantidade', sa.Numeric(10, 3), nullable=True),
        sa.Column('valor_venda', sa.Numeric(10, 2), nullable=True),
        sa.Column('valor_custo', sa.Numeric(10, 2), nullable=True),
        sa.Column('tipo_calculo', sa.String(50), nullable=True),
        sa.Column('valor_base_calculo', sa.Numeric(10, 2), nullable=True),
        sa.Column('percentual_comissao', sa.Numeric(5, 2), nullable=True),
        sa.Column('valor_comissao', sa.Numeric(10, 2), nullable=True),
        sa.Column('valor_comissao_gerada', sa.Numeric(10, 2), nullable=False),
        sa.Column('percentual_pago', sa.Numeric(5, 2), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pendente'),
        sa.Column('valor_base_original', sa.Numeric(10, 2), nullable=True),
        sa.Column('valor_base_comissionada', sa.Numeric(10, 2), nullable=True),
        sa.Column('percentual_aplicado', sa.Numeric(5, 2), nullable=True),
        sa.Column('valor_pago_referencia', sa.Numeric(10, 2), nullable=True),
        sa.Column('parcela_numero', sa.Integer(), nullable=True),
        sa.Column('data_pagamento', sa.Date(), nullable=True),
        sa.Column('forma_pagamento', sa.String(50), nullable=True),
        sa.Column('valor_pago', sa.Numeric(10, 2), nullable=True),
        sa.Column('saldo_restante', sa.Numeric(10, 2), nullable=True),
        sa.Column('data_estorno', sa.Date(), nullable=True),
        sa.Column('motivo_estorno', sa.Text(), nullable=True),
        sa.Column('observacao_pagamento', sa.Text(), nullable=True),
        sa.Column('data_criacao', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('data_atualizacao', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar índices para melhor performance
    op.create_index('ix_comissoes_itens_venda_id', 'comissoes_itens', ['venda_id'])
    op.create_index('ix_comissoes_itens_funcionario_id', 'comissoes_itens', ['funcionario_id'])
    op.create_index('ix_comissoes_itens_status', 'comissoes_itens', ['status'])
    op.create_index('ix_comissoes_itens_data_venda', 'comissoes_itens', ['data_venda'])
    op.create_index('ix_comissoes_itens_tenant_id', 'comissoes_itens', ['tenant_id'])
    
    # Criar foreign keys
    op.create_foreign_key(
        'fk_comissoes_itens_venda',
        'comissoes_itens', 'vendas',
        ['venda_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_comissoes_itens_funcionario',
        'comissoes_itens', 'clientes',
        ['funcionario_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('comissoes_itens')
