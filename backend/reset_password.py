"""Script temporário para resetar senha do admin"""
import bcrypt
import psycopg2

# Gerar novo hash usando bcrypt diretamente
nova_senha = "admin123"
senha_bytes = nova_senha.encode('utf-8')
salt = bcrypt.gensalt()
senha_hash = bcrypt.hashpw(senha_bytes, salt).decode('utf-8')

print(f"Novo hash gerado: {senha_hash[:60]}...")

# Conectar ao PostgreSQL
conn = psycopg2.connect(
    'postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db'
)
cursor = conn.cursor()

# Atualizar senha (coluna = hashed_password)
cursor.execute(
    "UPDATE users SET hashed_password = %s WHERE email = %s",
    (senha_hash, 'admin@test.com')
)
conn.commit()

print(f"Senha atualizada! Linhas afetadas: {cursor.rowcount}")

# Verificar usuário
cursor.execute("SELECT id, email, nome FROM users WHERE email = 'admin@test.com'")
user = cursor.fetchone()
print(f"Usuário confirmado: ID={user[0]}, Email={user[1]}, Nome={user[2]}")

conn.close()
print("\n✅ SENHA RESETADA COM SUCESSO!")
print("Nova senha: admin123")
