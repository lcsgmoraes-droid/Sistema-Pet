"""
Verifica estrutura da tabela cliente_segmentos
"""
import sys
from pathlib import Path
import psycopg2

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import get_database_url

def verify_table():
    """Verifica a estrutura da tabela cliente_segmentos"""
    
    # Extrai informações da connection string PostgreSQL
    db_url = get_database_url()
    
    if not db_url.startswith('postgresql://'):
        print("❌ Este script é apenas para PostgreSQL")
        return False
    
    # Parse da URL
    db_url = db_url.replace('postgresql://', '')
    user_pass, host_port_db = db_url.split('@')
    user, password = user_pass.split(':')
    host_port, dbname = host_port_db.split('/')
    host, port = host_port.split(':')
    
    try:
        # Conecta ao PostgreSQL
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        # Verifica a estrutura da tabela
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'cliente_segmentos'
            ORDER BY ordinal_position;
        """)
        
        print("\n📋 Estrutura atual da tabela cliente_segmentos:")
        print("-" * 70)
        print(f"{'Coluna':<25} | {'Tipo':<20} | {'NULL':<10}")
        print("-" * 70)
        
        has_tenant_id = False
        for row in cursor.fetchall():
            print(f"{row[0]:<25} | {row[1]:<20} | {row[2]:<10}")
            if row[0] == 'tenant_id':
                has_tenant_id = True
        print("-" * 70)
        
        # Verifica índices
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'cliente_segmentos'
            ORDER BY indexname;
        """)
        
        print("\n🔍 Índices criados:")
        print("-" * 70)
        for row in cursor.fetchall():
            print(f"  {row[0]}")
        print("-" * 70)
        
        # Verifica constraints
        cursor.execute("""
            SELECT conname, contype
            FROM pg_constraint
            WHERE conrelid = 'cliente_segmentos'::regclass
            ORDER BY conname;
        """)
        
        print("\n🔒 Constraints:")
        print("-" * 70)
        for row in cursor.fetchall():
            constraint_types = {
                'p': 'PRIMARY KEY',
                'f': 'FOREIGN KEY',
                'u': 'UNIQUE',
                'c': 'CHECK'
            }
            print(f"  {row[0]:<40} | {constraint_types.get(row[1], row[1])}")
        print("-" * 70)
        
        cursor.close()
        conn.close()
        
        return has_tenant_id
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🔍 VERIFICANDO ESTRUTURA DA TABELA cliente_segmentos")
    print("=" * 70)
    
    has_tenant_id = verify_table()
    
    print()
    if has_tenant_id:
        print("✅ Coluna tenant_id encontrada!")
    else:
        print("❌ Coluna tenant_id NÃO encontrada - precisa aplicar migration")
