"""add_tenant_columns_to_chat_tables

Revision ID: 20260216_chat_tenant
Revises: 20260216_fix_racas
Create Date: 2026-02-16 16:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260216_chat_tenant'
down_revision = '20260216_fix_racas'
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to conversas_ia
    op.add_column('conversas_ia', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('conversas_ia', sa.Column('created_at', sa.DateTime(timezone=True), 
                                            server_default=sa.text('now()'), nullable=True))
    op.add_column('conversas_ia', sa.Column('updated_at', sa.DateTime(timezone=True), 
                                            server_default=sa.text('now()'), nullable=True))
    
    # Populate tenant_id from first cliente in the system (fallback)
    op.execute("""
        UPDATE conversas_ia 
        SET tenant_id = (SELECT tenant_id FROM clientes LIMIT 1)
        WHERE tenant_id IS NULL
    """)
    
    # Create indexes
    op.create_index('ix_conversas_ia_tenant_id', 'conversas_ia', ['tenant_id'])
    
    # Add columns to mensagens_chat
    op.add_column('mensagens_chat', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('mensagens_chat', sa.Column('created_at', sa.DateTime(timezone=True), 
                                              server_default=sa.text('now()'), nullable=True))
    op.add_column('mensagens_chat', sa.Column('updated_at', sa.DateTime(timezone=True), 
                                              server_default=sa.text('now()'), nullable=True))
    
    # Populate tenant_id for mensagens_chat from their conversas
    op.execute("""
        UPDATE mensagens_chat m
        SET tenant_id = c.tenant_id
        FROM conversas_ia c
        WHERE m.conversa_id = c.id
    """)
    
    # Create indexes
    op.create_index('ix_mensagens_chat_tenant_id', 'mensagens_chat', ['tenant_id'])


def downgrade():
    # Drop indexes and columns from mensagens_chat
    op.drop_index('ix_mensagens_chat_tenant_id', table_name='mensagens_chat')
    op.drop_column('mensagens_chat', 'updated_at')
    op.drop_column('mensagens_chat', 'created_at')
    op.drop_column('mensagens_chat', 'tenant_id')
    
    # Drop indexes and columns from conversas_ia
    op.drop_index('ix_conversas_ia_tenant_id', table_name='conversas_ia')
    op.drop_column('conversas_ia', 'updated_at')
    op.drop_column('conversas_ia', 'created_at')
    op.drop_column('conversas_ia', 'tenant_id')
