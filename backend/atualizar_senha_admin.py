import sqlite3
from app.auth import hash_password

db_path = r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend\petshop.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Atualizar senha do admin
nova_senha_hash = hash_password("123456")
cursor.execute("UPDATE users SET hashed_password = ? WHERE email = 'admin@test.com'", (nova_senha_hash,))
conn.commit()

print("Senha atualizada para '123456'")
print(f"Hash: {nova_senha_hash[:30]}...")

conn.close()
