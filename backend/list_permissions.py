import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "petshop_db",
    "user": "petshop_user",
    "password": "petshop_password_2026"
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("SELECT id, code FROM permissions ORDER BY code")
permissions = cur.fetchall()
print("📋 Permissões cadastradas no sistema:\n")
for perm_id, code in permissions:
    print(f"   {perm_id:3d} - {code}")

cur.close()
conn.close()
