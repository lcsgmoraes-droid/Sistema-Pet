# Script simplificado - Criar apenas usuário admin
from legacy_script_env import connect_database, required_env

print("\n🔗 Conectando no banco PROD...")

try:
    conn_prod = connect_database("PROD_DATABASE_URL", "DATABASE_URL")
    admin_password_hash = required_env("ADMIN_PASSWORD_HASH")
    print("✅ Conectado!")
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)

cur = conn_prod.cursor()

print("\n👤 Criando usuário admin...")
try:
    # Verificar se tabela users existe
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'users'
        )
    """)
    tabela_existe = cur.fetchone()[0]

    if not tabela_existe:
        print("❌ Tabela 'users' não existe!")
        print("⚠️  Execute as migrations primeiro!")
        exit(1)

    # Verificar se admin já existe
    cur.execute("SELECT id FROM users WHERE email = 'admin@petshop.com'")
    admin_existente = cur.fetchone()

    if admin_existente:
        print(f"✅ Usuário admin já existe com ID: {admin_existente[0]}")
    else:
        # Criar usuário admin
        cur.execute(
            """
            INSERT INTO users (
                email, 
                hashed_password, 
                nome, 
                is_active, 
                is_admin,
                tenant_id,
                nome_loja
            ) VALUES (
                'admin@petshop.com',
                %s,
                'Administrador',
                true,
                true,
                gen_random_uuid(),
                'Pet Shop - Piloto'
            )
            RETURNING id
        """,
            (admin_password_hash,),
        )
        result = cur.fetchone()
        conn_prod.commit()

        if result:
            print(f"✅ Usuário admin criado com ID: {result[0]}")
        else:
            print("❌ Falha ao criar admin")

except Exception as e:
    print(f"❌ Erro: {e}")
    conn_prod.rollback()
    exit(1)

cur.close()
conn_prod.close()

print("\n" + "=" * 60)
print("   ✅ BANCO DE PRODUÇÃO PRONTO!")
print("=" * 60)
print("\n📋 Login inicial:")
print("   Email: admin@petshop.com")
print("   Senha: definida pelo hash em ADMIN_PASSWORD_HASH")
print("\n🔴 IMPORTANTE:")
print("   1. Altere a senha após o primeiro login")
print("   2. Configure formas de pagamento, DRE, etc no sistema")
print("\n🎯 Próximo passo:")
print("   docker-compose -f docker-compose.production-local.yml up -d backend-prod\n")
