"""Teste direto de login usando o código do backend"""
import sys
sys.path.insert(0, '.')

import psycopg2
from app.auth import verify_password

# Conectar ao PostgreSQL
conn = psycopg2.connect(
    'postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db'
)
cursor = conn.cursor()

# Buscar usuário
cursor.execute("SELECT id, email, nome, hashed_password FROM users WHERE email = 'admin@test.com'")
user = cursor.fetchone()

if user:
    print(f"Usuario encontrado:")
    print(f"  ID: {user[0]}")
    print(f"  Email: {user[1]}")
    print(f"  Nome: {user[2]}")
    print(f"  Hash: {user[3][:60]}...")
    
    # Testar senha usando a função do backend
    senha = "admin123"
    hash_db = user[3]
    
    print(f"\nTestando senha '{senha}'...")
    resultado = verify_password(senha, hash_db)
    
    if resultado:
        print("SENHA CORRETA - Login deveria funcionar!")
    else:
        print("SENHA INCORRETA - Problema na verificacao!")
else:
    print("Usuario nao encontrado!")

conn.close()
