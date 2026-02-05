"""
Script para adicionar coluna tenant_id à tabela lembretes
"""
import psycopg2
from uuid import UUID

# Configuração do banco
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "petshop_db",
    "user": "petshop_user",
    "password": "petshop_password_2026"
}

# ID do tenant padrão
TENANT_ID = "7be8dad7-8956-4758-b7bc-855a5259fe2b"

def adicionar_tenant_id_lembretes():
    """Adiciona coluna tenant_id à tabela lembretes"""
    
    conn = None
    try:
        print("=" * 60)
        print("ADICIONANDO TENANT_ID À TABELA LEMBRETES")
        print("=" * 60)
        
        # Conectar ao banco
        print("\n[1] Conectando ao banco de dados...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("    ✅ Conectado!")
        
        # Verificar se a coluna já existe
        print("\n[2] Verificando se coluna tenant_id já existe...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='lembretes' AND column_name='tenant_id'
        """)
        
        if cursor.fetchone():
            print("    ⚠️  Coluna tenant_id já existe!")
            return
        
        print("    ℹ️  Coluna não existe, será criada")
        
        # Adicionar coluna tenant_id
        print("\n[3] Adicionando coluna tenant_id...")
        cursor.execute("""
            ALTER TABLE lembretes 
            ADD COLUMN tenant_id UUID
        """)
        print("    ✅ Coluna adicionada!")
        
        # Preencher com tenant padrão para registros existentes
        print(f"\n[4] Preenchendo registros existentes com tenant_id = {TENANT_ID}...")
        cursor.execute("""
            UPDATE lembretes 
            SET tenant_id = %s 
            WHERE tenant_id IS NULL
        """, (TENANT_ID,))
        rows_updated = cursor.rowcount
        print(f"    ✅ {rows_updated} registros atualizados!")
        
        # Tornar coluna NOT NULL
        print("\n[5] Tornando coluna NOT NULL...")
        cursor.execute("""
            ALTER TABLE lembretes 
            ALTER COLUMN tenant_id SET NOT NULL
        """)
        print("    ✅ Coluna configurada como NOT NULL!")
        
        # Adicionar Foreign Key
        print("\n[6] Adicionando Foreign Key para tenants...")
        cursor.execute("""
            ALTER TABLE lembretes 
            ADD CONSTRAINT lembretes_tenant_id_fkey 
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        """)
        print("    ✅ Foreign Key adicionada!")
        
        # Adicionar índice
        print("\n[7] Criando índice para tenant_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_lembretes_tenant_id 
            ON lembretes(tenant_id)
        """)
        print("    ✅ Índice criado!")
        
        # Commit
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n❌ ERRO: {e}")
        raise
    
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("\n🔌 Conexão fechada")

if __name__ == "__main__":
    adicionar_tenant_id_lembretes()
