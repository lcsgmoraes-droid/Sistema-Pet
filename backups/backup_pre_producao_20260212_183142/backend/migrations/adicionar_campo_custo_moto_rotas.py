"""
ETAPA 11.1 - Adicionar campo custo_moto às rotas de entrega
Permite separar custo do entregador e custo da moto para dashboard financeiro
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL não encontrada")
        return
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    try:
        print("🔧 Verificando se campo custo_moto já existe...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'rotas_entrega' 
            AND column_name = 'custo_moto'
        """)
        
        if cursor.fetchone():
            print("✅ Campo custo_moto já existe")
            return
        
        print("📝 Adicionando campo custo_moto...")
        cursor.execute("""
            ALTER TABLE rotas_entrega
            ADD COLUMN custo_moto NUMERIC(10, 2) DEFAULT 0.00
        """)
        
        conn.commit()
        print("✅ Campo custo_moto adicionado com sucesso!")
        print("📊 Agora custo_real = custo_entregador + custo_moto")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
