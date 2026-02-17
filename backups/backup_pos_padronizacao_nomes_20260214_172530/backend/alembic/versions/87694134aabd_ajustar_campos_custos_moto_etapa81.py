"""ajustar_campos_custos_moto_etapa81

Revision ID: 87694134aabd
Revises: 6b592d755fb9
Create Date: 2026-02-01 10:29:44.261312

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '87694134aabd'
down_revision = '6b592d755fb9'
branch_labels = None
depends_on = None


def upgrade():
    """
    Ajusta nomenclatura dos campos para padrão ETAPA 8.1:
    - Renomeia km_troca_kit -> km_troca_kit_traseiro
    - Renomeia custo_troca_kit -> custo_kit_traseiro
    - Adiciona licenciamento_mensal (mantém licenciamento_anual)
    """
    from sqlalchemy import inspect
    from alembic import context
    
    conn = context.get_bind()
    inspector = inspect(conn)
    existing_columns = [c['name'] for c in inspector.get_columns('configuracoes_custo_moto')]
    
    # Renomear km_troca_kit para km_troca_kit_traseiro
    if 'km_troca_kit' in existing_columns and 'km_troca_kit_traseiro' not in existing_columns:
        op.alter_column(
            'configuracoes_custo_moto',
            'km_troca_kit',
            new_column_name='km_troca_kit_traseiro'
        )
    
    # Renomear custo_troca_kit para custo_kit_traseiro
    if 'custo_troca_kit' in existing_columns and 'custo_kit_traseiro' not in existing_columns:
        op.alter_column(
            'configuracoes_custo_moto',
            'custo_troca_kit',
            new_column_name='custo_kit_traseiro'
        )
    
    # Adicionar licenciamento_mensal (mantém licenciamento_anual para compatibilidade)
    if 'licenciamento_mensal' not in existing_columns:
        op.add_column(
            'configuracoes_custo_moto',
            sa.Column('licenciamento_mensal', sa.Numeric(10, 2), nullable=True)
        )


def downgrade():
    """Reverter alterações"""
    op.drop_column('configuracoes_custo_moto', 'licenciamento_mensal')
    op.alter_column('configuracoes_custo_moto', 'custo_kit_traseiro', new_column_name='custo_troca_kit')
    op.alter_column('configuracoes_custo_moto', 'km_troca_kit_traseiro', new_column_name='km_troca_kit')
