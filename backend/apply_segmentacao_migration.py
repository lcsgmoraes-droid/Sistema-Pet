"""
Script para aplicar migration de segmentação de clientes
Cria a tabela cliente_segmentos
"""

import sqlite3
import os
from pathlib import Path

# Definir caminhos
BACKEND_DIR = Path(__file__).parent
MIGRATIONS_DIR = BACKEND_DIR / "app" / "migrations"
DB_PATH = BACKEND_DIR / "petshop.db"
MIGRATION_FILE = MIGRATIONS_DIR / "create_cliente_segmentos_table.sql"


def aplicar_migration():
    """Aplica a migration de segmentação de clientes"""
    
    print("=" * 60)
    print("MIGRATION: Segmentação Automática de Clientes")
    print("=" * 60)
    
    # Verificar se arquivo de migration existe
    if not MIGRATION_FILE.exists():
        print(f"❌ Arquivo de migration não encontrado: {MIGRATION_FILE}")
        return False
    
    # Verificar se banco existe
    if not DB_PATH.exists():
        print(f"❌ Banco de dados não encontrado: {DB_PATH}")
        return False
    
    print(f"✅ Arquivo de migration: {MIGRATION_FILE}")
    print(f"✅ Banco de dados: {DB_PATH}")
    print()
    
    # Ler SQL da migration
    with open(MIGRATION_FILE, 'r', encoding='utf-8') as f:
        sql_migration = f.read()
    
    # Conectar ao banco
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        print("📝 Executando migration SQL...")
        
        # Executar migration (SQLite aceita múltiplas statements com executescript)
        cursor.executescript(sql_migration)
        
        conn.commit()
        print("✅ Migration executada com sucesso!")
        print()
        
        # Verificar se tabela foi criada
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='cliente_segmentos'
        """)
        
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ Tabela 'cliente_segmentos' criada com sucesso!")
            
            # Listar colunas
            cursor.execute("PRAGMA table_info(cliente_segmentos)")
            columns = cursor.fetchall()
            
            print("\n📋 Estrutura da tabela:")
            print("-" * 60)
            for col in columns:
                col_id, name, type_, notnull, default, pk = col
                nullable = "NOT NULL" if notnull else "NULL"
                pk_flag = "PRIMARY KEY" if pk else ""
                print(f"  {name:20s} {type_:15s} {nullable:10s} {pk_flag}")
            
            # Listar índices
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='cliente_segmentos'
            """)
            indices = cursor.fetchall()
            
            if indices:
                print("\n🔍 Índices criados:")
                print("-" * 60)
                for idx in indices:
                    print(f"  - {idx[0]}")
            
            print()
            print("=" * 60)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            
            return True
        else:
            print("❌ Tabela não foi criada!")
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Erro ao executar migration: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    sucesso = aplicar_migration()
    
    if sucesso:
        print("\n🚀 Próximos passos:")
        print("   1. Reiniciar o backend: cd backend && uvicorn app.main:app --reload")
        print("   2. Testar endpoints em /docs")
        print("   3. Recalcular segmentos: POST /segmentacao/recalcular-todos")
        print()
    else:
        print("\n❌ Migration falhou. Verifique os erros acima.")
