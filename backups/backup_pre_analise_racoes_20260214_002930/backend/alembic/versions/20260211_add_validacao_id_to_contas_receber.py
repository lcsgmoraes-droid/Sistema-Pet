"""Add validacao_id to contas_receber

Revision ID: 20260211_add_validacao_id
Revises: bb08aab30ba2
Create Date: 2026-02-11 16:00:00.000000

Descrição:
- Adiciona campo validacao_id em contas_receber
- Cria índice para performance
- Vincula parcela com validação que a processou
- EVITA DUPLA MOVIMENTAÇÃO quando rodar duas validações no mesmo período

Motivação:
- Ponto crítico #1 da revisão da Fase 2
- Sem este campo, se o usuário rodar duas validações para o mesmo período,
  as parcelas podem ser processadas duas vezes
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260211_add_validacao_id'
down_revision = 'bb08aab30ba2'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar campo validacao_id em contas_receber
    op.add_column(
        'contas_receber',
        sa.Column(
            'validacao_id',
            sa.Integer,
            sa.ForeignKey('conciliacao_validacoes.id', ondelete='SET NULL'),
            nullable=True,
            comment='Validação que processou esta parcela (evita reprocessamento)'
        )
    )
    
    # Criar índice para performance
    op.create_index(
        'ix_contas_receber_validacao_id',
        'contas_receber',
        ['validacao_id']
    )


def downgrade():
    # Remover índice
    op.drop_index('ix_contas_receber_validacao_id', table_name='contas_receber')
    
    # Remover campo
    op.drop_column('contas_receber', 'validacao_id')
