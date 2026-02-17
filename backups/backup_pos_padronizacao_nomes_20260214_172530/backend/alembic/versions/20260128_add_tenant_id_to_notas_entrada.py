"""add tenant_id to notas_entrada

Revision ID: 20260128_nota_tenant
Revises: 20260127_opp_events
Create Date: 2026-01-28 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260128_nota_tenant'
down_revision = '20260127_opp_events'
branch_labels = None
depends_on = None


def upgrade():
    # Add tenant_id column to notas_entrada
    op.add_column('notas_entrada', 
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Set a default tenant_id for existing records (get from users table)
    op.execute("""
        UPDATE notas_entrada ne
        SET tenant_id = u.tenant_id
        FROM users u
        WHERE ne.user_id = u.id
        AND ne.tenant_id IS NULL
    """)
    
    # Make tenant_id NOT NULL after setting values
    op.alter_column('notas_entrada', 'tenant_id', nullable=False)
    
    # Add index for tenant_id
    op.create_index(op.f('ix_notas_entrada_tenant_id'), 'notas_entrada', ['tenant_id'], unique=False)
    
    # Add tenant_id column to notas_entrada_itens
    op.add_column('notas_entrada_itens', 
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Set tenant_id for notas_entrada_itens from the parent nota_entrada
    op.execute("""
        UPDATE notas_entrada_itens nei
        SET tenant_id = ne.tenant_id
        FROM notas_entrada ne
        WHERE nei.nota_entrada_id = ne.id
        AND nei.tenant_id IS NULL
    """)
    
    # Make tenant_id NOT NULL after setting values
    op.alter_column('notas_entrada_itens', 'tenant_id', nullable=False)
    
    # Add index for tenant_id
    op.create_index(op.f('ix_notas_entrada_itens_tenant_id'), 'notas_entrada_itens', ['tenant_id'], unique=False)


def downgrade():
    # Drop indexes first
    op.drop_index(op.f('ix_notas_entrada_itens_tenant_id'), table_name='notas_entrada_itens')
    op.drop_index(op.f('ix_notas_entrada_tenant_id'), table_name='notas_entrada')
    
    # Drop columns
    op.drop_column('notas_entrada_itens', 'tenant_id')
    op.drop_column('notas_entrada', 'tenant_id')
