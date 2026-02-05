"""Ativar Simples Nacional"""
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='petshop_db',
    user='petshop_user',
    password='petshop_password_2026'
)
cur = conn.cursor()

# Ativar Simples
cur.execute("""
    UPDATE empresa_config_fiscal 
    SET simples_ativo = true, 
        simples_aliquota_vigente = 6.0, 
        simples_anexo = 'III'
    WHERE id = 1
""")
conn.commit()

print('✅ Simples Nacional ativado!')

# Verificar
cur.execute("""
    SELECT id, simples_ativo, simples_aliquota_vigente, simples_anexo 
    FROM empresa_config_fiscal 
    WHERE id = 1
""")
result = cur.fetchone()
print(f'ID: {result[0]}, Ativo: {result[1]}, Alíquota: {result[2]}%, Anexo: {result[3]}')

cur.close()
conn.close()
