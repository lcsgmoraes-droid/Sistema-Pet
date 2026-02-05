"""Atualizar versão do alembic para audit_logs migration"""
import psycopg2
from app.config import get_database_url

db_url = get_database_url()
parts = db_url.replace('postgresql://', '').split('@')
user_pass = parts[0].split(':')
host_db = parts[1].split('/')

user = user_pass[0]
password = user_pass[1]
host_port = host_db[0].split(':')
host = host_port[0]
port = host_port[1] if len(host_port) > 1 else '5432'
database = host_db[1]

print(f"Conectando ao banco: {database}@{host}:{port}")

conn = psycopg2.connect(
    host=host,
    port=port,
    database=database,
    user=user,
    password=password
)

cursor = conn.cursor()

try:
    # Update alembic version
    cursor.execute("""
        UPDATE alembic_version SET version_num = '3e9f678b9c43' WHERE version_num = '2d87cec25bcc';
    """)
    
    conn.commit()
    print("✅ Alembic version atualizada para 3e9f678b9c43 (audit_logs tenant_id)")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Erro: {e}")
    
finally:
    cursor.close()
    conn.close()
