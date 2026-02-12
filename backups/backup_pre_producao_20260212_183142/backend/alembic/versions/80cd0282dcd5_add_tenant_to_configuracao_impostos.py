"""add_tenant_to_configuracao_impostos

Revision ID: 80cd0282dcd5
Revises: 084f5b4fe721
Create Date: 2026-01-27 15:02:17.885419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80cd0282dcd5'
down_revision: Union[str, Sequence[str], None] = '084f5b4fe721'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona tenant_id à tabela configuracao_impostos"""
    from sqlalchemy.dialects.postgresql import UUID
    
    # Adicionar coluna tenant_id
    op.add_column('configuracao_impostos', sa.Column(
        'tenant_id',
        UUID(as_uuid=True),
        nullable=False
    ))
    
    # Criar foreign key para tenants
    op.create_foreign_key(
        'fk_config_impostos_tenant',
        'configuracao_impostos', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Criar índice
    op.create_index(
        'ix_config_impostos_tenant_id',
        'configuracao_impostos',
        ['tenant_id']
    )
    
    print("✅ configuracao_impostos agora está isolado por tenant")


def downgrade() -> None:
    """Remove tenant_id de configuracao_impostos"""
    op.drop_index('ix_config_impostos_tenant_id')
    op.drop_constraint('fk_config_impostos_tenant', 'configuracao_impostos', type_='foreignkey')
    op.drop_column('configuracao_impostos', 'tenant_id')

