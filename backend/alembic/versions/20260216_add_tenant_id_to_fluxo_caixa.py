"""add_tenant_id_to_fluxo_caixa

Revision ID: 20260216_tenant_fluxo
Revises: 20260215_add_percentual_online_loja_contas_pagar
Create Date: 2026-02-16 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20260216_tenant_fluxo'
down_revision: Union[str, Sequence[str], None] = '20260215_add_percentual_online_loja_contas_pagar'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona tenant_id à tabela fluxo_caixa"""
    
    # Adicionar coluna tenant_id (nullable primeiro)
    op.add_column('fluxo_caixa', sa.Column('tenant_id', postgresql.UUID(), nullable=True))
    
    # Atualizar registros existentes com o primeiro tenant
    op.execute("""
        UPDATE fluxo_caixa
        SET tenant_id = (SELECT id FROM tenants ORDER BY created_at LIMIT 1)
        WHERE tenant_id IS NULL
    """)
    
    # Tornar coluna NOT NULL
    op.alter_column('fluxo_caixa', 'tenant_id', nullable=False)
    
    # Criar índice
    op.create_index('ix_fluxo_caixa_tenant_id', 'fluxo_caixa', ['tenant_id'])
    
    # Criar foreign key
    op.create_foreign_key(
        'fk_fluxo_caixa_tenant',
        'fluxo_caixa', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Remove tenant_id da tabela fluxo_caixa"""
    op.drop_constraint('fk_fluxo_caixa_tenant', 'fluxo_caixa', type_='foreignkey')
    op.drop_index('ix_fluxo_caixa_tenant_id', table_name='fluxo_caixa')
    op.drop_column('fluxo_caixa', 'tenant_id')
