"""
Script para adicionar tenant_id às tabelas de Fluxo de Caixa (ABA 5)
- fluxo_caixa
- indices_saude_caixa
- projecao_fluxo_caixa
"""
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import get_database_url

def add_tenant_to_table(conn, table_name, fk_column=None):
    """Adiciona tenant_id a uma tabela"""
    
    print(f"\n{'='*70}")
    print(f"Processando tabela: {table_name}")
    print(f"{'='*70}")
    
    # Verifica se a coluna já existe
    print(f"1. Verificando se tenant_id já existe em {table_name}...")
    result = conn.execute(text(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='{table_name}' AND column_name='tenant_id'
    """))
    
    if result.fetchone() is not None:
        print(f"   ✓ tenant_id já existe em {table_name}")
        return True
    
    print(f"   → Coluna não existe, adicionando...")
    
    # Adiciona a coluna
    print(f"\n2. Adicionando coluna tenant_id...")
    conn.execute(text(f"""
        ALTER TABLE {table_name}
        ADD COLUMN tenant_id UUID
    """))
    conn.commit()
    print(f"   ✓ Coluna adicionada")
    
    # Popula tenant_id a partir de users
    print(f"\n3. Populando tenant_id...")
    conn.execute(text(f"""
        UPDATE {table_name} t
        SET tenant_id = u.tenant_id
        FROM users u
        WHERE t.usuario_id = u.id
        AND t.tenant_id IS NULL
    """))
    conn.commit()
    print(f"   ✓ tenant_id populado")
    
    # Torna NOT NULL
    print(f"\n4. Tornando tenant_id NOT NULL...")
    conn.execute(text(f"""
        ALTER TABLE {table_name}
        ALTER COLUMN tenant_id SET NOT NULL
    """))
    conn.commit()
    print(f"   ✓ tenant_id é NOT NULL")
    
    # Adiciona índice
    print(f"\n5. Adicionando índice...")
    conn.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_{table_name}_tenant_id 
        ON {table_name}(tenant_id)
    """))
    conn.commit()
    print(f"   ✓ Índice criado")
    
    # Adiciona created_at e updated_at se não existir
    for col in ['created_at', 'updated_at']:
        print(f"\n6. Verificando {col}...")
        result = conn.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='{table_name}' AND column_name='{col}'
        """))
        
        if result.fetchone() is None:
            print(f"   Adicionando {col}...")
            conn.execute(text(f"""
                ALTER TABLE {table_name}
                ADD COLUMN {col} TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
            """))
            conn.commit()
            print(f"   ✓ {col} adicionado")
        else:
            print(f"   ✓ {col} já existe")
    
    return True

def main():
    """Adiciona tenant_id às tabelas de Fluxo de Caixa"""
    
    print("=" * 70)
    print("🔧 ADICIONANDO tenant_id às tabelas de Fluxo de Caixa (ABA 5)")
    print("=" * 70)
    
    engine = create_engine(get_database_url())
    
    with engine.connect() as conn:
        try:
            # Tabelas do Fluxo de Caixa
            tables = [
                'fluxo_caixa',
                'indices_saude_caixa',
                'projecao_fluxo_caixa'
            ]
            
            for table in tables:
                add_tenant_to_table(conn, table)
            
            print("\n" + "=" * 70)
            print("✅ TODAS AS MIGRATIONS COMPLETAS!")
            print("=" * 70)
            print("\n⚠️  IMPORTANTE: Reinicie o container backend:")
            print("   docker-compose -f docker-compose.development.yml restart backend")
            print()
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            conn.rollback()
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
