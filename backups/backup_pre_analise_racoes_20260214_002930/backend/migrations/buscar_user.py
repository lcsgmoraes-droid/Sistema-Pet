import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

# Listar tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabelas = cursor.fetchall()
print("Tabelas:", [t[0] for t in tabelas])

# Buscar usuário
for nome_tabela in ['users', 'user', 'usuarios', 'usuario']:
    try:
        cursor.execute(f"SELECT id, username FROM {nome_tabela} LIMIT 1")
        user = cursor.fetchone()
        if user:
            print(f"\nEncontrado na tabela '{nome_tabela}':")
            print(f"ID: {user[0]}, Username: {user[1]}")
            break
    except:
        continue

conn.close()
