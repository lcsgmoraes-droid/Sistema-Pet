"""
Tornar campos dre_subcategoria_id e canal nullable em contas_pagar
Necessário para permitir criação de contas a pagar de NF-e sem classificação DRE
"""
import psycopg2
import os

# Conexão com banco de dados
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/petshop_dev'
).replace('postgresql+psycopg2://', 'postgresql://')  # Remover driver SQLAlchemy

def run_migration():
    """Altera constraints NOT NULL para permitir valores null"""
    
    print("🔧 Conectando ao banco de dados...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("📝 Alterando constraint de dre_subcategoria_id...")
        cursor.execute("""
            ALTER TABLE contas_pagar 
            ALTER COLUMN dre_subcategoria_id DROP NOT NULL;
        """)
        print("   ✅ dre_subcategoria_id agora é nullable")
        
        print("📝 Alterando constraint de canal...")
        cursor.execute("""
            ALTER TABLE contas_pagar 
            ALTER COLUMN canal DROP NOT NULL;
        """)
        print("   ✅ canal agora é nullable")
        
        conn.commit()
        print("\n✅ Migration concluída com sucesso!")
        print("💡 Campos dre_subcategoria_id e canal agora aceitam valores null")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro na migration: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
