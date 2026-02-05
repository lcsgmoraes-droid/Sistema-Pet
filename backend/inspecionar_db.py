import sqlite3
import os

# Tentar com sistema.db primeiro
paths = [
    "app/sistema.db",
    "app/petshop.db", 
    "petshop.db",
    "sistema.db"
]

for path in paths:
    if os.path.exists(path):
        print(f"\n✅ Encontrado: {path}")
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%comissoes%'")
            tables = cursor.fetchall()
            if tables:
                print(f"   Tabelas encontradas:")
                for table in tables:
                    print(f"   - {table[0]}")
                    # Verificar colunas
                    cursor.execute(f"PRAGMA table_info({table[0]})")
                    cols = cursor.fetchall()
                    print(f"     Colunas: {', '.join([c[1] for c in cols])}")
            conn.close()
        except Exception as e:
            print(f"   Erro: {e}")
    else:
        print(f"❌ Não encontrado: {path}")
