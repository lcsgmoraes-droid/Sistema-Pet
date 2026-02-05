"""fix fiscal tenant_id to uuid

Revision ID: fix_fiscal_tenant_id
Revises: 
Create Date: 2026-01-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fix_fiscal_tenant_id'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Alterar tenant_id de INTEGER para UUID em produto_config_fiscal (se existir)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'produto_config_fiscal'
            ) THEN
                ALTER TABLE produto_config_fiscal 
                ALTER COLUMN tenant_id TYPE UUID USING tenant_id::text::uuid;
            END IF;
        END $$;
    """)
    
    # Alterar tenant_id de INTEGER para UUID em kit_config_fiscal (se existir)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'kit_config_fiscal'
            ) THEN
                ALTER TABLE kit_config_fiscal 
                ALTER COLUMN tenant_id TYPE UUID USING tenant_id::text::uuid;
            END IF;
        END $$;
    """)
    
    print("✅ Colunas tenant_id alteradas de INTEGER para UUID")


def downgrade():
    # Reverter de UUID para INTEGER (se necessário)
    op.execute("""
        ALTER TABLE produto_config_fiscal 
        ALTER COLUMN tenant_id TYPE INTEGER USING tenant_id::text::integer
    """)
    
    op.execute("""
        ALTER TABLE kit_config_fiscal 
        ALTER COLUMN tenant_id TYPE INTEGER USING tenant_id::text::integer
    """)
