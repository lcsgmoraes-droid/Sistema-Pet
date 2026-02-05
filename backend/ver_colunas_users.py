import sqlite3

db_path = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\petshop.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Listar colunas da tabela users
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
print("Colunas da tabela 'users':")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
