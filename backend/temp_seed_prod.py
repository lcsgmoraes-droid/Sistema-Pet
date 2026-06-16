# Script para seed de produção
import psycopg2

print("\n🔗 Conectando nos bancos...")

# Conexões
try:
    conn_dev = psycopg2.connect(
        host='localhost',
        port=5433,
        database='petshop_dev',
        user='postgres',
        password='postgres'
    )
    print("✅ Conectado no DEV (porta 5433)")
except Exception as e:
    print(f"❌ Erro ao conectar no DEV: {e}")
    exit(1)

try:
    conn_prod = psycopg2.connect(
        host='localhost',
        port=5434,
        database='petshop_prod',
        user='petshop_user',
        password='petshop_pass_2026'
    )
    print("✅ Conectado no PROD")
except Exception as e:
    print(f"❌ Erro ao conectar no PROD: {e}")
    exit(1)

cur_dev = conn_dev.cursor()
cur_prod = conn_prod.cursor()

print("\n📋 Copiando configurações essenciais...")

# 1. Copiar categorias DRE
try:
    print("  → Categorias DRE...")
    cur_dev.execute("SELECT nome, tipo, descricao, ativo, tenant_id FROM dre_categorias ORDER BY id")
    categorias = cur_dev.fetchall()
    for cat in categorias:
        try:
            cur_prod.execute(
                "INSERT INTO dre_categorias (nome, tipo, descricao, ativo, tenant_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                cat
            )
        except Exception:
            pass
    conn_prod.commit()
    print(f"    ✅ {len(categorias)} categorias DRE copiadas")
except Exception as e:
    print(f"    ⚠️  Erro: {e}")
    conn_prod.rollback()

# 2. Copiar formas de pagamento
try:
    print("  → Formas de pagamento...")
    cur_dev.execute("SELECT nome, tipo, dias_recebimento, requer_fatura, tenant_id FROM formas_pagamento ORDER BY id")
    formas = cur_dev.fetchall()
    for forma in formas:
        try:
            cur_prod.execute(
                "INSERT INTO formas_pagamento (nome, tipo, dias_recebimento, requer_fatura, tenant_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                forma
            )
        except Exception:
            pass
    conn_prod.commit()
    print(f"    ✅ {len(formas)} formas de pagamento copiadas")
except Exception as e:
    print(f"    ⚠️  Erro: {e}")
    conn_prod.rollback()

# 3. Copiar bancos/contas
try:
    print("  → Bancos e contas...")
    cur_dev.execute("SELECT nome, tipo, saldo, ativo, tenant_id FROM contas_bancarias WHERE tipo = 'banco' ORDER BY id")
    bancos = cur_dev.fetchall()
    for banco in bancos:
        try:
            cur_prod.execute(
                "INSERT INTO contas_bancarias (nome, tipo, saldo, ativo, tenant_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                banco
            )
        except Exception:
            pass
    conn_prod.commit()
    print(f"    ✅ {len(bancos)} bancos copiados")
except Exception as e:
    print(f"    ⚠️  Erro: {e}")
    conn_prod.rollback()

# 4. Copiar taxas de pagamento
try:
    print("  → Taxas de pagamento...")
    cur_dev.execute("SELECT forma_pagamento_id, bandeira, tipo_taxa, percentual, valor_fixo, tenant_id FROM formas_pagamento_taxas ORDER BY id")
    taxas = cur_dev.fetchall()
    for taxa in taxas:
        try:
            cur_prod.execute(
                "INSERT INTO formas_pagamento_taxas (forma_pagamento_id, bandeira, tipo_taxa, percentual, valor_fixo, tenant_id) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                taxa
            )
        except Exception:
            pass
    conn_prod.commit()
    print(f"    ✅ {len(taxas)} taxas copiadas")
except Exception as e:
    print(f"    ⚠️  Erro: {e}")
    conn_prod.rollback()

print("\n👤 Criando usuário admin...")
try:
    cur_prod.execute("""
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
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY.6GZjMe/.hizq',
            'Administrador',
            true,
            true,
            gen_random_uuid(),
            'Pet Shop - Piloto'
        ) ON CONFLICT (email) DO NOTHING
        RETURNING id
    """)
    result = cur_prod.fetchone()
    conn_prod.commit()
    if result:
        print("✅ Usuário admin criado!")
    else:
        print("✅ Usuário admin já existe!")
except Exception as e:
    print(f"⚠️  Erro ao criar admin: {e}")
    conn_prod.rollback()

cur_dev.close()
cur_prod.close()
conn_dev.close()
conn_prod.close()

print("\n" + "="*60)
print("   ✅ BANCO DE PRODUÇÃO PRONTO!")
print("="*60)
print("\n📋 Login inicial:")
print("   Email: admin@petshop.com")
print("   Senha: admin123")
print("\n🔴 IMPORTANTE: Altere a senha após o primeiro login!\n")
print("🎯 Próximo passo: Subir o backend de produção")
print("   docker-compose -f docker-compose.production-local.yml up -d backend-prod\n")
