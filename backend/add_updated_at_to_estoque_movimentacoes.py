"""
Script para adicionar coluna updated_at em estoque_movimentacoes
"""
from sqlalchemy import create_engine, text
from app.config import get_database_url, DATABASE_TYPE

if DATABASE_TYPE != "postgresql":
    print(f"ℹ Database type is {DATABASE_TYPE}, not PostgreSQL.")
    print("ℹ Este script é específico para PostgreSQL.")
    exit(0)

engine = create_engine(get_database_url())

print("🔧 Adicionando coluna updated_at em estoque_movimentacoes...")

with engine.begin() as conn:
    # Verifica se a coluna já existe
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='estoque_movimentacoes' 
        AND column_name='updated_at';
    """))
    
    if result.scalar():
        print("ℹ️ Coluna updated_at já existe!")
    else:
        # Adiciona a coluna
        conn.execute(text("""
            ALTER TABLE estoque_movimentacoes 
            ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """))
        
        # Preenche com created_at para registros existentes
        conn.execute(text("""
            UPDATE estoque_movimentacoes 
            SET updated_at = created_at 
            WHERE updated_at IS NULL;
        """))
        
        print("✅ Coluna updated_at adicionada com sucesso!")
        print("✅ Valores inicializados com created_at")

print("🚀 Migração completa!")
print("✅ Reinicie o backend para testar as vendas.")
