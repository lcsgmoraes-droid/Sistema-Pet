#!/usr/bin/env python3
"""
=============================================================================
SCRIPT DE LIMPEZA - Remover dados de teste e mock
=============================================================================
Remove todos os dados de teste do banco e reseta para estado limpo
SEMPRE faz backup antes de limpar
=============================================================================
"""

import os
import sys
import subprocess
from datetime import datetime

# Cores
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
BOLD = '\033[1m'
NC = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{BOLD}{'=' * 80}{NC}")
    print(f"{BLUE}{BOLD}{text.center(80)}{NC}")
    print(f"{BLUE}{BOLD}{'=' * 80}{NC}\n")

def print_step(text):
    print(f"{YELLOW}▶ {text}{NC}")

def print_success(text):
    print(f"{GREEN}✓ {text}{NC}")

def print_error(text):
    print(f"{RED}✗ {text}{NC}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{NC}")

def run_command(cmd, shell=True):
    """Executa comando e retorna output"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def backup_before_clean(container_name):
    """Faz backup antes de limpar"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_pre_limpeza_{timestamp}.dump.gz"
    
    print_step("Fazendo backup de segurança antes de limpar...")
    
    cmd = f"docker exec {container_name} sh -c 'PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h postgres -U $POSTGRES_USER -d $POSTGRES_DB -F c | gzip > /backups/{backup_file}'"
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print_success(f"Backup criado: backups/{backup_file}")
        return True
    else:
        print_error(f"Falha no backup: {stderr}")
        return False

def get_table_counts(container_name, db_name, user):
    """Retorna contagem de registros por tabela"""
    print_step("Verificando dados existentes...")
    
    query = """
    SELECT 
        schemaname || '.' || tablename as table_name,
        (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
    FROM (
        SELECT 
            schemaname, 
            tablename, 
            query_to_xml(format('select count(*) as cnt from %I.%I', schemaname, tablename), false, true, '') as xml_count
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY tablename
    ) t
    WHERE (xpath('/row/cnt/text()', xml_count))[1]::text::int > 0;
    """
    
    cmd = f'docker exec {container_name} psql -U {user} -d {db_name} -t -c "{query}"'
    success, stdout, stderr = run_command(cmd)
    
    if success and stdout.strip():
        print(f"\n{BOLD}Tabelas com dados:{NC}")
        for line in stdout.strip().split('\n'):
            if '|' in line:
                table, count = [x.strip() for x in line.split('|')]
                print(f"  • {table}: {count} registros")
        return True
    else:
        print("  (Banco vazio ou erro ao consultar)")
        return False

def clean_database(container_name, db_name, user):
    """Limpa todos os dados do banco mantendo estrutura"""
    print_step("Limpando dados do banco...")
    
    # Script SQL para truncate de todas as tabelas
    truncate_script = """
    DO $$ 
    DECLARE 
        r RECORD;
    BEGIN
        -- Desabilitar foreign keys temporariamente
        SET session_replication_role = 'replica';
        
        -- Truncar todas as tabelas exceto alembic_version
        FOR r IN (
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename != 'alembic_version'
        ) LOOP
            EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
            RAISE NOTICE 'Truncated: %', r.tablename;
        END LOOP;
        
        -- Reabilitar foreign keys
        SET session_replication_role = 'origin';
        
        RAISE NOTICE 'Database cleaned successfully!';
    END $$;
    """
    
    # Salvar script em arquivo temporário
    script_file = "/tmp/truncate_all.sql"
    cmd = f'docker exec {container_name} sh -c "cat > {script_file} << \'EOF\'\n{truncate_script}\nEOF"'
    run_command(cmd)
    
    # Executar script
    cmd = f'docker exec {container_name} psql -U {user} -d {db_name} -f {script_file}'
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print_success("Banco de dados limpo com sucesso!")
        # Mostrar notices do PostgreSQL
        if "Truncated:" in stdout:
            print("\nTabelas limpas:")
            for line in stdout.split('\n'):
                if "Truncated:" in line:
                    table = line.split("Truncated:")[-1].strip()
                    print(f"  ✓ {table}")
        return True
    else:
        print_error(f"Erro ao limpar banco: {stderr}")
        return False

def clean_uploads(uploads_dir="uploads"):
    """Limpa diretório de uploads"""
    print_step("Limpando arquivos de upload...")
    
    if not os.path.exists(uploads_dir):
        print_warning(f"Diretório {uploads_dir} não existe")
        return True
    
    count = 0
    for root, dirs, files in os.walk(uploads_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
                count += 1
            except Exception as e:
                print_warning(f"Erro ao remover {file}: {e}")
    
    if count > 0:
        print_success(f"{count} arquivo(s) removido(s)")
    else:
        print("  (Nenhum arquivo para remover)")
    
    return True

def reset_sequences(container_name, db_name, user):
    """Reseta sequences para começar do ID 1"""
    print_step("Resetando sequences (IDs)...")
    
    reset_script = """
    DO $$ 
    DECLARE 
        r RECORD;
    BEGIN
        FOR r IN (
            SELECT sequence_name 
            FROM information_schema.sequences 
            WHERE sequence_schema = 'public'
        ) LOOP
            EXECUTE 'ALTER SEQUENCE ' || quote_ident(r.sequence_name) || ' RESTART WITH 1';
            RAISE NOTICE 'Reset: %', r.sequence_name;
        END LOOP;
        RAISE NOTICE 'All sequences reset!';
    END $$;
    """
    
    script_file = "/tmp/reset_sequences.sql"
    cmd = f'docker exec {container_name} sh -c "cat > {script_file} << \'EOF\'\n{reset_script}\nEOF"'
    run_command(cmd)
    
    cmd = f'docker exec {container_name} psql -U {user} -d {db_name} -f {script_file}'
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print_success("Sequences resetadas - próximos IDs começarão em 1")
        return True
    else:
        print_warning("Não foi possível resetar sequences (não crítico)")
        return True

def main():
    print_header("LIMPEZA DE DADOS DE TESTE E MOCK")
    
    # Detectar ambiente (staging ou local-prod)
    print("Qual ambiente você quer limpar?\n")
    print("1. Staging (petshop-staging-postgres)")
    print("2. Produção Local (petshop-local-prod-postgres)")
    print("3. Cancelar")
    
    choice = input("\nEscolha (1/2/3): ").strip()
    
    if choice == "1":
        container = "petshop-staging-postgres"
        db_name = "petshop_staging_db"
        user = "petshop_staging"
        env_name = "STAGING"
    elif choice == "2":
        container = "petshop-local-prod-postgres"
        db_name = "petshop_local_prod_db"
        user = "petshop_local_prod"
        env_name = "PRODUÇÃO LOCAL"
    else:
        print("\nOperação cancelada.")
        return 0
    
    print(f"\n{BOLD}Ambiente selecionado: {env_name}{NC}")
    
    # Verificar se container está rodando
    cmd = f"docker ps --filter name={container} --format '{{{{.Names}}}}'"
    success, stdout, stderr = run_command(cmd)
    
    if not success or container not in stdout:
        print_error(f"Container {container} não está rodando!")
        print("Inicie o ambiente primeiro.")
        return 1
    
    print_success(f"Container {container} está rodando")
    
    # Mostrar dados atuais
    get_table_counts(container, db_name, user)
    
    # Confirmação
    print(f"\n{RED}{BOLD}⚠️  ATENÇÃO ⚠️{NC}")
    print(f"{RED}Esta operação irá:{NC}")
    print(f"{RED}  • Fazer backup de segurança{NC}")
    print(f"{RED}  • APAGAR TODOS OS DADOS do banco {db_name}{NC}")
    print(f"{RED}  • Manter apenas a estrutura (tabelas/migrations){NC}")
    print(f"{RED}  • Resetar IDs para começar do 1{NC}")
    print(f"{RED}  • Limpar arquivos de upload{NC}")
    
    confirm = input(f"\n{BOLD}Deseja continuar? Digite 'LIMPAR' para confirmar: {NC}").strip()
    
    if confirm != "LIMPAR":
        print("\nOperação cancelada.")
        return 0
    
    print("\n" + "=" * 80)
    
    # 1. Backup de segurança
    if not backup_before_clean(container.replace('-postgres', '-backup')):
        print_error("Falha no backup! Operação cancelada por segurança.")
        return 1
    
    # 2. Limpar banco de dados
    if not clean_database(container, db_name, user):
        print_error("Falha ao limpar banco! Verifique os logs.")
        return 1
    
    # 3. Resetar sequences
    reset_sequences(container, db_name, user)
    
    # 4. Limpar uploads
    clean_uploads()
    
    # Verificar resultado
    print("\n" + "=" * 80)
    print_step("Verificando resultado...")
    has_data = get_table_counts(container, db_name, user)
    
    if not has_data:
        print(f"\n{GREEN}{BOLD}✓ BANCO COMPLETAMENTE LIMPO!{NC}")
    
    print("\n" + "=" * 80)
    print(f"{GREEN}{BOLD}LIMPEZA CONCLUÍDA COM SUCESSO!{NC}")
    print("=" * 80)
    
    print(f"\n{BOLD}Próximos passos:{NC}")
    print("1. Verificar backup em backups/backup_pre_limpeza_*.dump.gz")
    print("2. Começar a cadastrar dados reais da sua loja")
    print("3. Fazer backup periódico conforme usar o sistema")
    
    print(f"\n{BOLD}Para restaurar o backup (se necessário):{NC}")
    print("  Consulte: DISASTER_RECOVERY.md ou GUIA_DADOS_REAIS_LOCAL.md")
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Erro inesperado: {e}{NC}")
        sys.exit(1)
