"""add_tenant_id_to_lembretes

Revision ID: 20260215_add_tenant_id_lembretes
Revises: 20260215_add_missing_permissions
Create Date: 2026-02-15 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260215_add_tenant_id_lembretes'
down_revision: Union[str, Sequence[str], None] = '20260215_add_missing_permissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona coluna tenant_id na tabela lembretes"""
    
    # Verificar se a coluna já existe
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='lembretes' AND column_name='tenant_id'
    """))
    
    if result.fetchone() is None:
        # Adicionar coluna tenant_id
        op.add_column('lembretes', sa.Column('tenant_id', sa.UUID(), nullable=True))
        
        # Preencher tenant_id baseado no user_id
        op.execute("""
            UPDATE lembretes 
            SET tenant_id = users.tenant_id 
            FROM users 
            WHERE lembretes.user_id = users.id
        """)
        
        # Tornar a coluna NOT NULL após preencher
        op.alter_column('lembretes', 'tenant_id', nullable=False)
        
        # Criar índice
        op.create_index('ix_lembretes_tenant_id', 'lembretes', ['tenant_id'])
        
        print("✅ Coluna tenant_id adicionada à tabela lembretes")
    else:
        print("ℹ️  Coluna tenant_id já existe na tabela lembretes")


def downgrade() -> None:
    """Remove coluna tenant_id da tabela lembretes"""
    op.drop_index('ix_lembretes_tenant_id', 'lembretes')
    op.drop_column('lembretes', 'tenant_id')
    print("✅ Coluna tenant_id removida da tabela lembretes")
