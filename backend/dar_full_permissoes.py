#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: E402

"""
Script para dar TODAS as permissões ao usuário teste@teste.com
"""
import psycopg2

print("\n🔗 Conectando no banco PROD...")

import os

# Detectar se está dentro do Docker ou no host
DB_HOST = os.getenv('POSTGRES_HOST', 'petshop-prod-postgres')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = 'petshop_prod'  # Nome correto do banco
DB_USER = 'petshop_admin'  # Usuário admin que funciona
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'MUDE_ESTA_SENHA_AGORA_USE_SENHA_FORTE_2026')

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    print(f"✅ Conectado em {DB_HOST}:{DB_PORT}/{DB_NAME}!")
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)

cur = conn.cursor()

try:
    # 1. Buscar o usuário teste@teste.com
    print("\n👤 Buscando usuário teste@teste.com...")
    cur.execute("SELECT id, nome, tenant_id FROM users WHERE email = 'teste@teste.com'")
    user = cur.fetchone()
    
    if not user:
        print("❌ Usuário teste@teste.com não encontrado!")
        exit(1)
    
    user_id, nome, tenant_id = user
    print(f"✅ Usuário encontrado: {nome} (ID: {user_id}, Tenant: {tenant_id})")
    
    # 2. Buscar a role do usuário no tenant
    print("\n🔍 Buscando role do usuário...")
    cur.execute("""
        SELECT ut.role_id, r.name 
        FROM user_tenants ut
        JOIN roles r ON r.id = ut.role_id
        WHERE ut.user_id = %s AND ut.tenant_id = %s
    """, (user_id, tenant_id))
    
    user_role = cur.fetchone()
    
    if not user_role:
        print("❌ Usuário não tem role vinculada!")
        exit(1)
    
    role_id, role_name = user_role
    print(f"✅ Role: {role_name} (ID: {role_id})")
    
    # 3. Contar permissões atuais
    cur.execute("""
        SELECT COUNT(*) 
        FROM role_permissions 
        WHERE role_id = %s AND tenant_id = %s
    """, (role_id, tenant_id))
    
    count_atual = cur.fetchone()[0]
    print(f"📊 Permissões atuais: {count_atual}")
    
    # 4. Contar total de permissões no sistema
    cur.execute("SELECT COUNT(*) FROM permissions")
    total_perms = cur.fetchone()[0]
    print(f"📊 Total de permissões no sistema: {total_perms}")
    
    # 5. Adicionar TODAS as permissões à role
    print(f"\n🚀 Adicionando todas as {total_perms} permissões...")
    
    cur.execute("""
        INSERT INTO role_permissions (tenant_id, role_id, permission_id)
        SELECT %s, %s, p.id
        FROM permissions p
        WHERE NOT EXISTS (
            SELECT 1 FROM role_permissions rp 
            WHERE rp.role_id = %s 
            AND rp.tenant_id = %s 
            AND rp.permission_id = p.id
        )
    """, (tenant_id, role_id, role_id, tenant_id))
    
    novas = cur.rowcount
    conn.commit()
    
    # 6. Verificar permissões finais
    cur.execute("""
        SELECT COUNT(*) 
        FROM role_permissions 
        WHERE role_id = %s AND tenant_id = %s
    """, (role_id, tenant_id))
    
    count_final = cur.fetchone()[0]
    
    print(f"✅ {novas} novas permissões adicionadas!")
    print(f"✅ Total de permissões agora: {count_final}/{total_perms}")
    
    # 7. Listar algumas permissões para confirmar
    print("\n📋 Algumas permissões agora disponíveis:")
    cur.execute("""
        SELECT p.code, p.description
        FROM permissions p
        JOIN role_permissions rp ON rp.permission_id = p.id
        WHERE rp.role_id = %s AND rp.tenant_id = %s
        ORDER BY p.code
        LIMIT 10
    """, (role_id, tenant_id))
    
    for code, desc in cur.fetchall():
        print(f"   ✓ {code}: {desc}")
    
    print(f"\n{'='*60}")
    print("   ✅ USUÁRIO teste@teste.com COM TODAS AS PERMISSÕES!")
    print(f"{'='*60}")
    print("\n📧 Email: teste@teste.com")
    print("🔑 Senha: test123")
    print(f"👤 Nome: {nome}")
    print(f"🏢 Tenant: {tenant_id}")
    print(f"👔 Role: {role_name}")
    print(f"✅ Permissões: {count_final}/{total_perms}\n")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    conn.rollback()
    exit(1)
finally:
    cur.close()
    conn.close()
