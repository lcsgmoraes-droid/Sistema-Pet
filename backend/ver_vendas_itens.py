import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%venda%'")
tabelas = cursor.fetchall()

print("Tabelas com 'venda' no nome:")
for t in tabelas:
    print(f"  - {t[0]}")

print("\nVerificando campos de vendas_itens:")
try:
    cursor.execute("PRAGMA table_info(vendas_itens)")
    cols = cursor.fetchall()
    if cols:
        for c in cols:
            print(f"  {c[1]}")
    else:
        print("  Tabela vazia ou não existe")
except Exception as e:
    print(f"  Erro: {e}")

conn.close()
