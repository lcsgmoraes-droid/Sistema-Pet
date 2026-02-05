"""
Script para ver os valores RAW do banco de dados SQLite
"""
import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

# Ver estrutura da tabela
cursor.execute("PRAGMA table_info(contas_pagar)")
print("📊 Estrutura da tabela contas_pagar:")
print("=" * 80)
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\n💰 Valores no banco (RAW):")
print("=" * 80)

# Ver os valores
cursor.execute("""
    SELECT id, descricao, valor_original, valor_final
    FROM contas_pagar
""")

for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    print(f"  Descrição: {row[1]}")
    print(f"  Valor Original (raw): {row[2]}")
    print(f"  Valor Final (raw): {row[3]}")
    print()

conn.close()
