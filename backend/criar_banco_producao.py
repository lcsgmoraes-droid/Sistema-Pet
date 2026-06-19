"""
============================================================================
SCRIPT: Criar Banco de Produção Limpo
============================================================================

🎯 OBJETIVO:
Criar um banco de dados LIMPO para iniciar o piloto na loja.

✅ O QUE FAZ:
1. Conecta no banco de PRODUÇÃO (porta 5433)
2. Aplica todas as migrations (estrutura completa)
3. Copia APENAS configurações essenciais do DEV:
   - Categorias DRE
   - Formas de pagamento + taxas
   - Bancos
   - Templates NFC-e (se tiver)
4. Cria usuário admin de produção
5. NÃO copia: produtos, vendas, clientes, animais, NF-es

🚀 COMO USAR:
1. Suba o banco de produção:
   docker-compose -f docker-compose.production-local.yml up -d postgres-prod

2. Aguarde o banco ficar pronto (30 segundos)

3. Execute este script:
   python backend/criar_banco_producao.py

4. Pronto! Banco limpo criado!

============================================================================
"""

import os
import subprocess
import time

from legacy_script_env import database_url_from_env, required_env

# Cores para terminal
VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
AZUL = "\033[94m"
RESET = "\033[0m"


def print_header(texto):
    print(f"\n{AZUL}{'=' * 60}{RESET}")
    print(f"{AZUL}{texto.center(60)}{RESET}")
    print(f"{AZUL}{'=' * 60}{RESET}\n")


def print_sucesso(texto):
    print(f"{VERDE}✅ {texto}{RESET}")


def print_aviso(texto):
    print(f"{AMARELO}⚠️  {texto}{RESET}")


def print_erro(texto):
    print(f"{VERMELHO}❌ {texto}{RESET}")


def executar_comando(comando, descricao):
    """Executa um comando shell e mostra resultado"""
    print(f"\n{AZUL}➤{RESET} {descricao}...")
    resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)

    if resultado.returncode == 0:
        print_sucesso(f"{descricao} - OK")
        return True
    else:
        print_erro(f"{descricao} - FALHOU")
        if resultado.stderr:
            print(f"Erro: {resultado.stderr}")
        return False


def main():
    print_header("CRIAR BANCO DE PRODUÇÃO LIMPO")

    print("Este script vai:")
    print("1. Verificar se o banco de produção está rodando")
    print("2. Aplicar todas as migrations (estrutura)")
    print("3. Copiar configurações essenciais do DEV")
    print("4. Criar usuário admin")
    print("5. Deixar produtos, vendas, clientes VAZIOS\n")

    resposta = input(f"{AMARELO}🤔 Deseja continuar? (s/n): {RESET}").lower()
    if resposta != "s":
        print_aviso("Operação cancelada pelo usuário")
        return

    # ========================================================================
    # ETAPA 1: Verificar se banco de produção está rodando
    # ========================================================================
    print_header("ETAPA 1: Verificar Banco de Produção")

    resultado = subprocess.run(
        "docker ps --filter name=petshop-prod-postgres --format {{.Status}}",
        shell=True,
        capture_output=True,
        text=True,
    )

    if "Up" not in resultado.stdout:
        print_erro("Banco de produção NÃO está rodando!")
        print(f"\n{AMARELO}Execute primeiro:{RESET}")
        print(
            "docker-compose -f docker-compose.production-local.yml up -d postgres-prod\n"
        )
        return

    print_sucesso("Banco de produção está rodando!")

    # ========================================================================
    # ETAPA 2: Aguardar banco ficar pronto
    # ========================================================================
    print_header("ETAPA 2: Aguardar Banco Ficar Pronto")

    print("Aguardando 10 segundos para o banco inicializar...")
    time.sleep(10)
    print_sucesso("Pronto!")

    # ========================================================================
    # ETAPA 3: Aplicar migrations
    # ========================================================================
    print_header("ETAPA 3: Aplicar Migrations (Estrutura)")

    # Primeiro, configurar variáveis de ambiente para apontar para os bancos
    prod_database_url = database_url_from_env("PROD_DATABASE_URL", "DATABASE_URL")
    dev_database_url = database_url_from_env("DEV_DATABASE_URL")
    admin_password_hash = required_env("ADMIN_PASSWORD_HASH")
    os.environ["DATABASE_URL"] = prod_database_url
    os.environ["PROD_DATABASE_URL"] = prod_database_url
    os.environ["DEV_DATABASE_URL"] = dev_database_url
    os.environ["ADMIN_PASSWORD_HASH"] = admin_password_hash

    if not executar_comando(
        "cd backend && alembic upgrade head", "Aplicando migrations"
    ):
        print_erro("Falha ao aplicar migrations!")
        return

    # ========================================================================
    # ETAPA 4: Executar script de seed de produção
    # ========================================================================
    print_header("ETAPA 4: Copiar Configurações Essenciais")

    print(f"{AZUL}ℹ️  Vou criar um script Python para copiar as configurações...{RESET}")

    script_seed = """
# Script para seed de produção
import os

import psycopg2

# Conexões
conn_dev = psycopg2.connect(os.environ["DEV_DATABASE_URL"])
conn_prod = psycopg2.connect(os.environ["PROD_DATABASE_URL"])
admin_password_hash = os.environ["ADMIN_PASSWORD_HASH"]

cur_dev = conn_dev.cursor()
cur_prod = conn_prod.cursor()

print("\\n📋 Copiando configurações...")

# 1. Copiar categorias financeiras (DRE)
print("  → Categorias DRE...")
cur_dev.execute("SELECT nome, tipo, descricao, tenant_id FROM fin_categoria")
categorias = cur_dev.fetchall()
for cat in categorias:
    cur_prod.execute(
        "INSERT INTO fin_categoria (nome, tipo, descricao, tenant_id) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        cat
    )

# 2. Copiar formas de pagamento
print("  → Formas de pagamento...")
cur_dev.execute("SELECT nome, tipo, tenant_id FROM formas_pagamento")
formas = cur_dev.fetchall()
for forma in formas:
    cur_prod.execute(
        "INSERT INTO formas_pagamento (nome, tipo, tenant_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        forma
    )

# 3. Copiar bancos
print("  → Bancos...")
cur_dev.execute("SELECT nome, codigo, tenant_id FROM fin_conta WHERE tipo = 'banco'")
bancos = cur_dev.fetchall()
for banco in bancos:
    cur_prod.execute(
        "INSERT INTO fin_conta (nome, codigo, tipo, tenant_id) VALUES (%s, %s, 'banco', %s) ON CONFLICT DO NOTHING",
        banco
    )

conn_prod.commit()
print("✅ Configurações copiadas!\\n")

# 4. Criar usuário admin
print("📋 Criando usuário admin...")
cur_prod.execute(\"\"\"
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
    ) ON CONFLICT (email) DO NOTHING
\"\"\", (admin_password_hash,))
conn_prod.commit()
print("✅ Usuário admin criado!\\n")
print("   Email: admin@petshop.com")
print("   Senha: definida pelo hash em ADMIN_PASSWORD_HASH\\n")
print("   🔴 IMPORTANTE: Altere a senha após o primeiro login!\\n")

cur_dev.close()
cur_prod.close()
conn_dev.close()
conn_prod.close()

print("🎉 Banco de produção criado com sucesso!\\n")
"""

    # Salvar script temporário
    with open("temp_seed_prod.py", "w", encoding="utf-8") as f:
        f.write(script_seed)

    # Executar script
    if not executar_comando("python temp_seed_prod.py", "Copiando configurações"):
        print_erro("Falha ao copiar configurações!")
        return

    # Remover script temporário
    os.remove("temp_seed_prod.py")

    # ========================================================================
    # FINALIZAÇÃO
    # ========================================================================
    print_header("✅ BANCO DE PRODUÇÃO CRIADO COM SUCESSO!")

    print(f"\n{VERDE}O que foi feito:{RESET}")
    print("  ✅ Estrutura completa criada (todas as tabelas)")
    print("  ✅ Configurações copiadas (DRE, formas pagamento, bancos)")
    print("  ✅ Usuário admin criado")
    print("  ✅ Banco VAZIO (sem produtos, vendas, clientes)\n")

    print(f"{AMARELO}Próximos passos:{RESET}")
    print("  1. Subir o backend de produção:")
    print(
        "     docker-compose -f docker-compose.production-local.yml up -d backend-prod"
    )
    print("")
    print("  2. Acessar sistema:")
    print("     http://localhost:5174 (frontend apontando para porta 8001)")
    print("")
    print("  3. Fazer login:")
    print("     Email: admin@petshop.com")
    print("     Senha: definida pelo hash em ADMIN_PASSWORD_HASH")
    print("")
    print("  4. IMPORTANTE: Alterar senha após primeiro login!")
    print("")
    print(
        f"{AZUL}🎯 Agora você pode cadastrar produtos REAIS e começar o piloto!{RESET}\n"
    )


if __name__ == "__main__":
    main()
