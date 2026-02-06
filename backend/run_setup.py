"""
Setup emergencial do banco de dados para permitir login
"""
from sqlalchemy import create_engine, text
import sys

DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/postgres"

def setup_database():
    engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    
    with open('setup_login.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Executar statement por statement
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
    
    with engine.connect() as conn:
        for stmt in statements:
            if stmt:
                try:
                    print(f"Executando: {stmt[:80]}...")
                    result = conn.execute(text(stmt))
                    print("✅ OK")
                except Exception as e:
                    print(f"⚠️ {str(e)[:100]}")
    
    print("\n✨ Setup concluído!")

if __name__ == "__main__":
    setup_database()
