"""add_tenant_to_config_tributaria

Revision ID: 084f5b4fe721
Revises: 0f13697f08fb
Create Date: 2026-01-27 14:42:51.664099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '084f5b4fe721'
down_revision: Union[str, Sequence[str], None] = '0f13697f08fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona tenant_id e timestamps à tabela configuracao_tributaria"""
    from sqlalchemy.dialects.postgresql import UUID
    
    # Adicionar coluna tenant_id
    op.add_column('configuracao_tributaria', sa.Column(
        'tenant_id',
        UUID(as_uuid=True),
        nullable=False
    ))
    
    # Criar foreign key para tenants
    op.create_foreign_key(
        'fk_config_tributaria_tenant',
        'configuracao_tributaria', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Criar índice
    op.create_index(
        'ix_config_tributaria_tenant_id',
        'configuracao_tributaria',
        ['tenant_id']
    )
    
    # Adicionar created_at e updated_at
    op.add_column('configuracao_tributaria', sa.Column(
        'created_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    op.add_column('configuracao_tributaria', sa.Column(
        'updated_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()')
    ))
    
    print("✅ configuracao_tributaria agora está isolado por tenant")
    print("✅ TODAS as tabelas de IA agora têm tenant_id!")


def downgrade() -> None:
    """Remove tenant_id e timestamps de configuracao_tributaria"""
    op.drop_index('ix_config_tributaria_tenant_id')
    op.drop_constraint('fk_config_tributaria_tenant', 'configuracao_tributaria', type_='foreignkey')
    op.drop_column('configuracao_tributaria', 'tenant_id')
    op.drop_column('configuracao_tributaria', 'updated_at')
    op.drop_column('configuracao_tributaria', 'created_at')
