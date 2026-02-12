"""Add adquirente to conciliacao_recebimentos

Revision ID: 20260212_add_adquirente_conciliacao_recebimentos
Revises: 20260212_fix_historico_timestamps
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa


revision = '20260212_add_adquirente_conciliacao_recebimentos'
down_revision = '20260212_fix_historico_timestamps'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'conciliacao_recebimentos',
        sa.Column('adquirente', sa.String(length=100), nullable=True)
    )
    op.create_index(
        'ix_conciliacao_recebimentos_adquirente',
        'conciliacao_recebimentos',
        ['adquirente']
    )


def downgrade():
    op.drop_index('ix_conciliacao_recebimentos_adquirente', table_name='conciliacao_recebimentos')
    op.drop_column('conciliacao_recebimentos', 'adquirente')
