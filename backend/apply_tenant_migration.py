"""
Aplica migration de tenant_id na tabela cliente_segmentos
"""
import sys
from pathlib import Path
import psycopg2
from psycopg2 import sql

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import get_database_url

def apply_migration():
    """Aplica a migration add_tenant_id_to_cliente_segmentos"""
    
    migration_file = backend_dir / "app" / "migrations" / "add_tenant_id_to_cliente_segmentos.sql"
    
    if not migration_file.exists():
        print(f"❌ Arquivo de migration não encontrado: {migration_file}")
        return False
    
    # Lê o conteúdo da migration
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Extrai informações da connection string PostgreSQL
    db_url = get_database_url()
    
    if not db_url.startswith('postgresql://'):
        print("❌ Este script é apenas para PostgreSQL")
        return False
    
    # Parse da URL
    # postgresql://user:pass@host:port/dbname
    db_url = db_url.replace('postgresql://', '')
    user_pass, host_port_db = db_url.split('@')
    user, password = user_pass.split(':')
    host_port, dbname = host_port_db.split('/')
    host, port = host_port.split(':')
    
    try:
        # Conecta ao PostgreSQL
        print(f"🔌 Conectando ao PostgreSQL em {host}:{port}...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        conn.autocommit = False
        cursor = conn.cursor()
        
        print(f"📖 Aplicando migration: {migration_file.name}")
        
        # Executa a migration
        cursor.execute(migration_sql)
        conn.commit()
        
        print("✅ Migration aplicada com sucesso!")
        
        # Verifica a estrutura da tabela
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'cliente_segmentos'
            ORDER BY ordinal_position;
        """)
        
        print("\n📋 Estrutura atual da tabela cliente_segmentos:")
        print("-" * 60)
        for row in cursor.fetchall():
            print(f"  {row[0]:<20} | {row[1]:<15} | NULL: {row[2]}")
        print("-" * 60)
        
        # Verifica índices
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'cliente_segmentos'
            ORDER BY indexname;
        """)
        
        print("\n🔍 Índices criados:")
        print("-" * 60)
        for row in cursor.fetchall():
            print(f"  {row[0]}")
        print("-" * 60)
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar migration: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 APLICANDO MIGRATION: tenant_id em cliente_segmentos")
    print("=" * 60)
    print()
    
    success = apply_migration()
    
    print()
    if success:
        print("✅ Migration concluída com sucesso!")
        print("⚠️  IMPORTANTE: Reinicie o backend para aplicar as mudanças")
    else:
        print("❌ Migration falhou. Verifique os erros acima.")
        sys.exit(1)
