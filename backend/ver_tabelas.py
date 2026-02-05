import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tabelas em petshop.db:")
for t in tables:
    print(f"  - {t[0]}")
conn.close()
