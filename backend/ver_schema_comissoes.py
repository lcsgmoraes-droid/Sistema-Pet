import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='comissoes_itens'")
print(cursor.fetchone()[0])

conn.close()
