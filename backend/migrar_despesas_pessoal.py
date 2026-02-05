"""
Migração: Adicionar coluna despesas_pessoal nas tabelas DRE
Executar: python migrar_despesas_pessoal.py
"""
import sys
from sqlalchemy import text, inspect
from app.db import engine, SessionLocal

def adicionar_coluna_se_nao_existe(table_name: str, column_name: str, column_type: str):
    """Adiciona uma coluna se ela não existir"""
    inspector = inspect(engine)
    
    # Verificar se a tabela existe
    if table_name not in inspector.get_table_names():
        print(f"⚠️  Tabela {table_name} não existe, pulando...")
        return False
    
    # Verificar se a coluna já existe
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    
    if column_name in columns:
        print(f"✅ Coluna {table_name}.{column_name} já existe")
        return True
    
    # Adicionar a coluna
    try:
        with engine.connect() as conn:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT 0"
            conn.execute(text(sql))
            conn.commit()
        print(f"✅ Coluna {table_name}.{column_name} adicionada com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao adicionar {table_name}.{column_name}: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("🔄 MIGRAÇÃO: Adicionar despesas_pessoal nas tabelas DRE")
    print("="*60 + "\n")
    
    sucesso = True
    
    # 1. Adicionar na tabela dre_detalhe_canal
    print("1️⃣  Adicionando despesas_pessoal em dre_detalhe_canal...")
    if not adicionar_coluna_se_nao_existe('dre_detalhe_canal', 'despesas_pessoal', 'FLOAT'):
        sucesso = False
    
    # 2. Adicionar na tabela dre_consolidado
    print("\n2️⃣  Adicionando despesas_pessoal em dre_consolidado...")
    if not adicionar_coluna_se_nao_existe('dre_consolidado', 'despesas_pessoal', 'FLOAT'):
        sucesso = False
    
    print("\n" + "="*60)
    if sucesso:
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n💡 Agora as abas online (ML, Shopee) terão a linha 'Despesas com Pessoal'")
    else:
        print("⚠️  MIGRAÇÃO CONCLUÍDA COM AVISOS")
    print("="*60 + "\n")
    
    return 0 if sucesso else 1

if __name__ == "__main__":
    sys.exit(main())
