# ⚠️ LEGADO - NÃO USAR
import sqlite3

print("⚠️ Script LEGADO bloqueado! Use PostgreSQL.")
raise SystemExit("Use SessionLocal() do app.db")

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name')
tables = cursor.fetchall()
print('\n'.join([t[0] for t in tables]))
conn.close()
