import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

# Verificar tabelas whatsapp
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'whatsapp%'")
tables = cursor.fetchall()
print("Tabelas WhatsApp encontradas:")
for table in tables:
    print(f"  - {table[0]}")

# Dropar tabelas antigas
print("\nDropando tabelas antigas...")
for table in tables:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
        print(f"  ✓ Dropada: {table[0]}")
    except Exception as e:
        print(f"  ✗ Erro ao dropar {table[0]}: {e}")

conn.commit()
conn.close()
print("\n✅ Limpeza concluída!")
