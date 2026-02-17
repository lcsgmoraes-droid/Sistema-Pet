"""
Adiciona configuração de custo operacional de entrega
Migration: 006_adicionar_custo_operacional_entrega.py
"""
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent.parent / 'petshop.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Criar tabela de configuração de entregas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracao_entregas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modelo_custo TEXT NOT NULL DEFAULT 'taxa_fixa',
                taxa_fixa DECIMAL(10,2) DEFAULT 10.00,
                valor_por_km DECIMAL(10,2) DEFAULT 0,
                ativo INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Inserir configuração padrão
        cursor.execute("""
            INSERT INTO configuracao_entregas (modelo_custo, taxa_fixa)
            VALUES ('taxa_fixa', 10.00)
        """)
        
        conn.commit()
        print("✅ Tabela configuracao_entregas criada com sucesso!")
        print("✅ Configuração padrão inserida: Taxa fixa R$ 10,00")
        
    except sqlite3.Error as e:
        print(f"❌ Erro ao criar tabela: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
