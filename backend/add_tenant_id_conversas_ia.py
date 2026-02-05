"""
Script para adicionar tenant_id à tabela conversas_ia
"""
import sys
from pathlib import Path
import psycopg2
from sqlalchemy import create_engine, text

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import get_database_url

def add_tenant_id_to_conversas_ia():
    """Adiciona tenant_id à tabela conversas_ia"""
    
    engine = create_engine(get_database_url())
    
    with engine.connect() as conn:
        try:
            # Verifica se a coluna já existe
            print("Verificando se tenant_id já existe...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='conversas_ia' AND column_name='tenant_id'
            """))
            
            if result.fetchone() is None:
                print("✓ Coluna não existe, prosseguindo com adição...")
                
                # Adiciona a coluna tenant_id (nullable inicialmente)
                print("\n1. Adicionando coluna tenant_id...")
                conn.execute(text("""
                    ALTER TABLE conversas_ia 
                    ADD COLUMN tenant_id UUID
                """))
                conn.commit()
                print("   ✓ Coluna adicionada")
                
                # Popula tenant_id a partir da tabela users
                print("\n2. Populando tenant_id a partir de users...")
                conn.execute(text("""
                    UPDATE conversas_ia c
                    SET tenant_id = u.tenant_id
                    FROM users u
                    WHERE c.usuario_id = u.id
                    AND c.tenant_id IS NULL
                """))
                conn.commit()
                print("   ✓ tenant_id populado")
                
                # Torna tenant_id NOT NULL
                print("\n3. Tornando tenant_id NOT NULL...")
                conn.execute(text("""
                    ALTER TABLE conversas_ia 
                    ALTER COLUMN tenant_id SET NOT NULL
                """))
                conn.commit()
                print("   ✓ tenant_id é NOT NULL")
                
                # Adiciona índice
                print("\n4. Adicionando índice em tenant_id...")
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_conversas_ia_tenant_id 
                    ON conversas_ia(tenant_id)
                """))
                conn.commit()
                print("   ✓ Índice criado")
                
                # Adiciona created_at se não existir
                print("\n5. Verificando created_at...")
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='conversas_ia' AND column_name='created_at'
                """))
                
                if result.fetchone() is None:
                    print("   Adicionando created_at...")
                    conn.execute(text("""
                        ALTER TABLE conversas_ia 
                        ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                    """))
                    # Atualiza registros existentes
                    conn.execute(text("""
                        UPDATE conversas_ia 
                        SET created_at = criado_em 
                        WHERE created_at IS NULL
                    """))
                    conn.commit()
                    print("   ✓ created_at adicionado")
                else:
                    print("   ✓ created_at já existe")
                
                # Adiciona updated_at se não existir
                print("\n6. Verificando updated_at...")
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='conversas_ia' AND column_name='updated_at'
                """))
                
                if result.fetchone() is None:
                    print("   Adicionando updated_at...")
                    conn.execute(text("""
                        ALTER TABLE conversas_ia 
                        ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                    """))
                    # Atualiza registros existentes
                    conn.execute(text("""
                        UPDATE conversas_ia 
                        SET updated_at = COALESCE(atualizado_em, criado_em, NOW())
                        WHERE updated_at IS NULL
                    """))
                    conn.commit()
                    print("   ✓ updated_at adicionado")
                else:
                    print("   ✓ updated_at já existe")
                
                print("\n" + "=" * 70)
                print("✅ MIGRATION COMPLETA!")
                print("=" * 70)
                print("\n⚠️  IMPORTANTE: Reinicie o container backend:")
                print("   docker-compose -f docker-compose.development.yml restart backend")
                print()
                
                return True
            else:
                print("✓ Coluna tenant_id já existe em conversas_ia")
                return True
                
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            conn.rollback()
            return False

if __name__ == "__main__":
    print("=" * 70)
    print("🔧 ADICIONANDO tenant_id à tabela conversas_ia")
    print("=" * 70)
    print()
    
    success = add_tenant_id_to_conversas_ia()
    
    if not success:
        sys.exit(1)
