"""
Script de validação do fluxo de autenticação multi-tenant
"""
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

print("=" * 60)
print("VALIDACAO DO FLUXO MULTI-TENANT")
print("=" * 60)

conn = psycopg2.connect(
    host=host,
    port=port,
    database=database,
    user=user,
    password=password
)

cursor = conn.cursor()

try:
    # 1. Verificar estrutura da tabela user_sessions
    print("\n1. ESTRUTURA DA TABELA user_sessions:")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'user_sessions'
        ORDER BY ordinal_position;
    """)
    columns = cursor.fetchall()
    for col in columns:
        print(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
    
    # 2. Verificar sessões existentes
    print("\n2. SESSOES EXISTENTES:")
    cursor.execute("""
        SELECT 
            id,
            user_id,
            token_jti,
            tenant_id,
            created_at,
            revoked
        FROM user_sessions
        ORDER BY created_at DESC
        LIMIT 5;
    """)
    sessions = cursor.fetchall()
    if sessions:
        for sess in sessions:
            tenant_status = "COM TENANT" if sess[3] else "SEM TENANT"
            revoked_status = "REVOGADA" if sess[5] else "ATIVA"
            print(f"   - Sessao #{sess[0]} - User {sess[1]} - {tenant_status} - {revoked_status}")
            print(f"     JTI: {sess[2][:8]}...")
    else:
        print("   (Nenhuma sessao encontrada)")
    
    # 3. Verificar duplicações de JTI
    print("\n3. VERIFICACAO DE DUPLICACOES:")
    cursor.execute("""
        SELECT token_jti, COUNT(*) as count
        FROM user_sessions
        GROUP BY token_jti
        HAVING COUNT(*) > 1;
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        print("   ATENCAO: JTIs duplicados encontrados!")
        for dup in duplicates:
            print(f"      - JTI {dup[0][:8]}... aparece {dup[1]} vezes")
    else:
        print("   OK: Nenhum JTI duplicado")
    
    # 4. Verificar tenants disponíveis
    print("\n4. TENANTS NO SISTEMA:")
    cursor.execute("""
        SELECT id, name
        FROM tenants
        LIMIT 5;
    """)
    tenants = cursor.fetchall()
    if tenants:
        for tenant in tenants:
            print(f"   - {tenant[1]} (ID: {tenant[0]})")
    else:
        print("   ATENCAO: Nenhum tenant encontrado!")
    
    # 5. Verificar usuários com acesso a tenants
    print("\n5. USUARIOS COM ACESSO A TENANTS:")
    cursor.execute("""
        SELECT 
            u.email,
            COUNT(DISTINCT ut.tenant_id) as tenant_count
        FROM users u
        LEFT JOIN user_tenants ut ON u.id = ut.user_id
        GROUP BY u.id, u.email
        ORDER BY tenant_count DESC
        LIMIT 5;
    """)
    users = cursor.fetchall()
    for user_info in users:
        print(f"   - {user_info[0]}: {user_info[1]} tenant(s)")
    
    print("\n" + "=" * 60)
    print("VALIDACAO CONCLUIDA")
    print("=" * 60)
    
except Exception as e:
    print(f"\nERRO: {e}")
finally:
    cursor.close()
    conn.close()
