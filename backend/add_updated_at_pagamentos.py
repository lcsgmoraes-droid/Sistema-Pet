"""
Adicionar coluna updated_at na tabela pagamentos
"""
import psycopg2
import os

# Conexão com banco de dados
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/petshop_dev'
).replace('postgresql+psycopg2://', 'postgresql://')

def run_migration():
    """Adiciona coluna updated_at"""
    
    print("🔧 Conectando ao banco de dados...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("📝 Verificando se coluna updated_at existe...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='pagamentos' 
            AND column_name='updated_at';
        """)
        
        if cursor.fetchone():
            print("   ⚠️ Coluna updated_at já existe")
        else:
            print("📝 Adicionando coluna updated_at...")
            cursor.execute("""
                ALTER TABLE pagamentos 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            print("   ✅ Coluna updated_at adicionada")
            
            # Atualizar registros existentes
            print("📝 Atualizando registros existentes...")
            cursor.execute("""
                UPDATE pagamentos 
                SET updated_at = created_at 
                WHERE updated_at IS NULL;
            """)
            print("   ✅ Registros atualizados")
        
        conn.commit()
        print("\n✅ Migration concluída com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro na migration: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
