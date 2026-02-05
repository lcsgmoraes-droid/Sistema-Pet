import sqlite3
conn = sqlite3.connect("./petshop.db")
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE pets ADD COLUMN codigo TEXT")
    print("Coluna adicionada")
except:
    print("Coluna ja existe")
cursor.execute("SELECT id, cliente_id FROM pets WHERE codigo IS NULL OR codigo = ''''")
pets = cursor.fetchall()
for pet_id, cliente_id in pets:
    cursor.execute("SELECT codigo FROM clientes WHERE id = ?", (cliente_id,))
    result = cursor.fetchone()
    if result and result[0]:
        codigo = f"{result[0]}-PET-{pet_id:04d}"
    else:
        codigo = f"CLI{cliente_id:05d}-PET-{pet_id:04d}"
    cursor.execute("UPDATE pets SET codigo = ? WHERE id = ?", (codigo, pet_id))
    print(f"Pet {pet_id}: {codigo}")
conn.commit()
print(f"{len(pets)} pets atualizados")
conn.close()
