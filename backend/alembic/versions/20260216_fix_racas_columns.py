"""fix_racas_columns

Revision ID: 20260216_fix_racas
Revises: 20260216_especies_racas
Create Date: 2026-02-16 16:13:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260216_fix_racas'
down_revision = '20260216_especies_racas'
branch_labels = None
depends_on = None


def upgrade():
    # Rename old especie column to preserve data temporarily
    op.alter_column('racas', 'especie', new_column_name='especie_old', 
                    existing_type=sa.String(50), existing_nullable=False)
    
    # Add new columns
    op.add_column('racas', sa.Column('especie_id', sa.Integer(), nullable=True))
    op.add_column('racas', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('racas', sa.Column('updated_at', sa.DateTime(timezone=True), 
                                     server_default=sa.text('now()'), nullable=True))
    
    # Populate tenant_id from the first cliente in the system (fallback)
    op.execute("""
        UPDATE racas 
        SET tenant_id = (SELECT tenant_id FROM clientes LIMIT 1)
        WHERE tenant_id IS NULL
    """)
    
    # Try to match old especie names to especies.id by name
    op.execute("""
        UPDATE racas r
        SET especie_id = e.id
        FROM especies e
        WHERE LOWER(TRIM(r.especie_old)) = LOWER(TRIM(e.nome))
        AND r.tenant_id = e.tenant_id
    """)
    
    # For any racas that couldn't be matched, set to NULL (will need manual fix)
    # Or create a default "Não especificado" especie
    
    # Drop the old column
    op.drop_index('ix_racas_especie', table_name='racas')
    op.drop_column('racas', 'especie_old')
    
    # Create foreign key and indexes
    op.create_foreign_key('fk_racas_especie_id', 'racas', 'especies', ['especie_id'], ['id'])
    op.create_index('ix_racas_especie_id', 'racas', ['especie_id'])
    op.create_index('ix_racas_tenant_id', 'racas', ['tenant_id'])


def downgrade():
    # Reverse the changes
    op.drop_index('ix_racas_tenant_id', table_name='racas')
    op.drop_index('ix_racas_especie_id', table_name='racas')
    op.drop_constraint('fk_racas_especie_id', 'racas', type_='foreignkey')
    
    # Add back old especie column
    op.add_column('racas', sa.Column('especie_old', sa.String(50), nullable=True))
    
    # Try to restore old values from especies names
    op.execute("""
        UPDATE racas r
        SET especie_old = e.nome
        FROM especies e
        WHERE r.especie_id = e.id
    """)
    
    # Drop new columns
    op.drop_column('racas', 'updated_at')
    op.drop_column('racas', 'tenant_id')
    op.drop_column('racas', 'especie_id')
    
    # Rename back
    op.alter_column('racas', 'especie_old', new_column_name='especie',
                    existing_type=sa.String(50))
    op.create_index('ix_racas_especie', 'racas', ['especie'])
