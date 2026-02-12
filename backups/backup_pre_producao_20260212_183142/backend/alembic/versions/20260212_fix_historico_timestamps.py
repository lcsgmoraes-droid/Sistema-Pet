"""Fix historico_conciliacao timestamp column names

Revision ID: 20260212_fix_historico_timestamps
Revises: 20260212_add_historico_conciliacao
Create Date: 2026-02-12

Renomeia colunas criado_em/atualizado_em para created_at/updated_at
para compatibilidade com BaseTenantModel.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20260212_fix_historico_timestamps'
down_revision = '20260212_add_historico_conciliacao'
branch_labels = None
depends_on = None


def upgrade():
    # Renomear colunas de timestamp
    op.alter_column(
        'historico_conciliacao',
        'criado_em',
        new_column_name='created_at'
    )
    op.alter_column(
        'historico_conciliacao',
        'atualizado_em',
        new_column_name='updated_at'
    )
    
    # Renomear índice
    op.drop_index('ix_historico_criado_em', 'historico_conciliacao')
    op.create_index('ix_historico_created_at', 'historico_conciliacao', ['created_at'])


def downgrade():
    # Reverter mudanças
    op.drop_index('ix_historico_created_at', 'historico_conciliacao')
    op.create_index('ix_historico_criado_em', 'historico_conciliacao', ['criado_em'])
    
    op.alter_column(
        'historico_conciliacao',
        'created_at',
        new_column_name='criado_em'
    )
    op.alter_column(
        'historico_conciliacao',
        'updated_at',
        new_column_name='atualizado_em'
    )
