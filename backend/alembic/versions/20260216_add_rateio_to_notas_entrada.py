"""add_rateio_to_notas_entrada

Revision ID: 20260216_add_rateio_to_notas_entrada
Revises: 20260216_create_whatsapp_tables
Create Date: 2026-02-16 21:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260216_add_rateio_to_notas_entrada'
down_revision = '20260216_tenant_fluxo'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar colunas de rateio à tabela notas_entrada
    op.add_column('notas_entrada', sa.Column('tipo_rateio', sa.String(length=20), server_default='loja', nullable=True))
    op.add_column('notas_entrada', sa.Column('percentual_online', sa.Float(), server_default='0', nullable=True))
    op.add_column('notas_entrada', sa.Column('percentual_loja', sa.Float(), server_default='100', nullable=True))
    op.add_column('notas_entrada', sa.Column('valor_online', sa.Float(), server_default='0', nullable=True))
    op.add_column('notas_entrada', sa.Column('valor_loja', sa.Float(), server_default='0', nullable=True))


def downgrade():
    # Remover colunas de rateio
    op.drop_column('notas_entrada', 'valor_loja')
    op.drop_column('notas_entrada', 'valor_online')
    op.drop_column('notas_entrada', 'percentual_loja')
    op.drop_column('notas_entrada', 'percentual_online')
    op.drop_column('notas_entrada', 'tipo_rateio')
