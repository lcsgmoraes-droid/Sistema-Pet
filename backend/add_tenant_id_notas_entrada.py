"""
Script to add tenant_id to notas_entrada tables
"""
from sqlalchemy import create_engine, text
from app.config import get_database_url

def add_tenant_id_to_notas_entrada():
    """Add tenant_id column to notas_entrada and notas_entrada_itens tables"""
    engine = create_engine(get_database_url())
    
    with engine.connect() as conn:
        try:
            # Check if tenant_id column already exists in notas_entrada
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='notas_entrada' AND column_name='tenant_id'
            """))
            
            if result.fetchone() is None:
                print("Adding tenant_id column to notas_entrada table...")
                
                # Add tenant_id column to notas_entrada
                conn.execute(text("""
                    ALTER TABLE notas_entrada 
                    ADD COLUMN tenant_id UUID
                """))
                conn.commit()
                print("✓ Column added to notas_entrada")
                
                # Set tenant_id from users table
                print("Setting tenant_id values from users...")
                conn.execute(text("""
                    UPDATE notas_entrada ne
                    SET tenant_id = u.tenant_id
                    FROM users u
                    WHERE ne.user_id = u.id
                    AND ne.tenant_id IS NULL
                """))
                conn.commit()
                print("✓ tenant_id values set")
                
                # Make tenant_id NOT NULL
                print("Making tenant_id NOT NULL...")
                conn.execute(text("""
                    ALTER TABLE notas_entrada 
                    ALTER COLUMN tenant_id SET NOT NULL
                """))
                conn.commit()
                print("✓ tenant_id is now NOT NULL")
                
                # Add index
                print("Adding index on tenant_id...")
                conn.execute(text("""
                    CREATE INDEX ix_notas_entrada_tenant_id ON notas_entrada(tenant_id)
                """))
                conn.commit()
                print("✓ Index created")
            else:
                print("✓ tenant_id column already exists in notas_entrada")
                
            # Check if tenant_id column already exists in notas_entrada_itens
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='notas_entrada_itens' AND column_name='tenant_id'
            """))
            
            if result.fetchone() is None:
                print("\nAdding tenant_id column to notas_entrada_itens table...")
                
                # Add tenant_id column to notas_entrada_itens
                conn.execute(text("""
                    ALTER TABLE notas_entrada_itens 
                    ADD COLUMN tenant_id UUID
                """))
                conn.commit()
                print("✓ Column added to notas_entrada_itens")
                
                # Set tenant_id from parent nota_entrada
                print("Setting tenant_id values from notas_entrada...")
                conn.execute(text("""
                    UPDATE notas_entrada_itens nei
                    SET tenant_id = ne.tenant_id
                    FROM notas_entrada ne
                    WHERE nei.nota_entrada_id = ne.id
                    AND nei.tenant_id IS NULL
                """))
                conn.commit()
                print("✓ tenant_id values set")
                
                # Make tenant_id NOT NULL
                print("Making tenant_id NOT NULL...")
                conn.execute(text("""
                    ALTER TABLE notas_entrada_itens 
                    ALTER COLUMN tenant_id SET NOT NULL
                """))
                conn.commit()
                print("✓ tenant_id is now NOT NULL")
                
                # Add index
                print("Adding index on tenant_id...")
                conn.execute(text("""
                    CREATE INDEX ix_notas_entrada_itens_tenant_id ON notas_entrada_itens(tenant_id)
                """))
                conn.commit()
                print("✓ Index created")
            else:
                print("✓ tenant_id column already exists in notas_entrada_itens")
                
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    add_tenant_id_to_notas_entrada()
