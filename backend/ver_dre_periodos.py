"""Ver estrutura dre_periodos"""
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='petshop_db',
    user='petshop_user',
    password='petshop_password_2026'
)
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns 
    WHERE table_name = 'dre_periodos' 
    ORDER BY ordinal_position
""")

print("Colunas dre_periodos:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} (NULL: {row[2]})")

cur.close()
conn.close()
