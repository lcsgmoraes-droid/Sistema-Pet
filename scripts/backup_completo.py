#!/usr/bin/env python3
"""
=============================================================================
BACKUP RÁPIDO - ARQUIVOS PRINCIPAIS
=============================================================================
Salva apenas os arquivos essenciais do projeto:
- Código fonte (backend, frontend, scripts)
- Configurações (.env)
- Documentação
- Docker configs
=============================================================================
"""

import os
import sys
import shutil
from datetime import datetime
import zipfile

# Cores
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
    print(f"{YELLOW}▶ [{datetime.now().strftime('%H:%M:%S')}] {text}{NC}")

def print_success(text):
    print(f"{GREEN}✓ {text}{NC}")

def get_size_mb(path):
    """Retorna tamanho em MB"""
    if os.path.isfile(path):
        return os.path.getsize(path) / (1024 * 1024)
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return total / (1024 * 1024)

def main():
    print_header("BACKUP RÁPIDO - ARQUIVOS PRINCIPAIS")
    
    # Timestamp para o backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_sistema_{timestamp}.zip"
    backup_path = os.path.join("backups", backup_name)
    
    print(f"{BOLD}Criando backup:{NC} {backup_name}\n")
    
    # Criar diretório de backups se não existir
    os.makedirs("backups", exist_ok=True)
    
    # ==========================================================================
    # DEFINIR O QUE SERÁ SALVO
    # ==========================================================================
    
    # Diretórios principais
    dirs_to_backup = [
        'backend',
        'frontend', 
        'scripts',
        'docs'
    ]
    
    # Arquivos importantes
    files_to_backup = [
        'docker-compose.staging.yml',
        'docker-compose.local-prod.yml',
        'docker-compose.yml',
        '.env.staging',
        '.env.local-prod',
        '.env.production.template',
        'DISASTER_RECOVERY.md',
        'GUIA_DADOS_REAIS_LOCAL.md',
        'GUIA_DEPLOY_PRODUCAO.md',
        'PROXIMOS_PASSOS.md',
        'README.md',
        'STAGING_QUICKSTART.md',
        'RELATORIO_FASE_8.2_LOGGING_ESTRUTURADO.md',
        'RELATORIO_FASE_8.3_RATE_LIMITING.md',
        'RELATORIO_FASE_8.4_DOCKER_STAGING.md',
        'INICIAR_BACKEND.bat',
        'INICIAR_FRONTEND.bat',
        'INICIAR_SISTEMA.bat',
        'INICIAR_LOCAL_PROD.bat',
        'BACKUP_COMPLETO.bat',
        'LIMPAR_DADOS_TESTE.bat'
    ]
    
    # ==========================================================================
    # CRIAR ZIP DO BACKUP
    # ==========================================================================
    print_step("Compactando arquivos...")
    
    total_files = 0
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Adicionar diretórios
        for dir_name in dirs_to_backup:
            if os.path.exists(dir_name):
                print(f"  Adicionando: {dir_name}/")
                for root, dirs, files in os.walk(dir_name):
                    # Filtrar exclusões
                    dirs[:] = [d for d in dirs if d not in [
                        '__pycache__', '.git', 'node_modules', 
                        '.venv', 'venv', '.pytest_cache', '.mypy_cache'
                    ]]
                    
                    for file in files:
                        if not file.endswith(('.pyc', '.log')):
                            file_path = os.path.join(root, file)
                            zipf.write(file_path)
                            total_files += 1
        
        # Adicionar arquivos individuais
        print(f"  Adicionando arquivos de configuração...")
        for file in files_to_backup:
            if os.path.exists(file):
                zipf.write(file)
                total_files += 1
    
    print_success(f"{total_files} arquivos compactados")
    
    # ==========================================================================
    # CRIAR README DO BACKUP
    # ==========================================================================
    print_step("Criando documentação do backup...")
    
    readme_content = f"""# BACKUP SISTEMA PET SHOP PRO

**Data:** {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
**Arquivo:** {backup_name}

## 📋 CONTEÚDO

Este backup contém os arquivos principais do sistema:

### Código Fonte:
- `backend/` - Aplicação FastAPI completa
- `frontend/` - Interface do usuário (se houver)
- `scripts/` - Scripts de automação
- `docs/` - Documentação técnica

### Configurações:
- `.env.staging` - Config ambiente staging
- `.env.local-prod` - Config produção local
- `.env.production.template` - Template produção
- `docker-compose.*.yml` - Orquestração Docker

### Documentação:
- `DISASTER_RECOVERY.md` - Plano de recuperação
- `GUIA_DADOS_REAIS_LOCAL.md` - Uso com dados reais
- `GUIA_DEPLOY_PRODUCAO.md` - Deploy em produção
- Outros documentos importantes

### Scripts de Inicialização:
- Arquivos .bat para Windows

## 🔄 COMO RESTAURAR

1. **Descompactar:**
   ```bash
   unzip {backup_name} -d /destino/
   ```

2. **Configurar ambiente:**
   ```bash
   cd /destino
   # Verificar e ajustar .env files
   ```

3. **Subir containers:**
   ```bash
   docker-compose -f docker-compose.staging.yml up -d
   ```

4. **Rodar migrações:**
   ```bash
   docker exec petshop-staging-backend alembic upgrade head
   ```

## ⚠️ IMPORTANTE

- Backup NÃO inclui: bancos de dados, uploads, node_modules
- Para backup completo do banco, use scripts específicos
- Guarde em local seguro (OneDrive, Google Drive)
- Mantenha múltiplas versões

## 📊 ESTATÍSTICAS

- Arquivos incluídos: {total_files}
- Tamanho: {get_size_mb(backup_path):.2f} MB
"""
    
    readme_path = os.path.join("backups", f"README_{timestamp}.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print_success("Documentação criada")
    
    final_size = get_size_mb(backup_path)
    
    # ==========================================================================
    # RESUMO FINAL
    # ==========================================================================
    print("\n" + "=" * 80)
    print(f"{GREEN}{BOLD}✓ BACKUP CRIADO COM SUCESSO!{NC}")
    print("=" * 80)
    
    print(f"\n{BOLD}Arquivo:{NC} {backup_path}")
    print(f"{BOLD}Tamanho:{NC} {final_size:.2f} MB")
    print(f"{BOLD}Total de arquivos:{NC} {total_files}")
    
    print(f"\n{BOLD}Conteúdo:{NC}")
    print("  ✓ Código fonte completo (backend, frontend, scripts)")
    print("  ✓ Configurações (.env files)")
    print("  ✓ Docker configs")
    print("  ✓ Documentação")
    print("  ✓ Scripts de inicialização")
    
    print(f"\n{BOLD}Próximos passos:{NC}")
    print("1. [RECOMENDADO] Copiar para local seguro:")
    print(f"   - OneDrive já está configurado nesta máquina")
    print(f"   - Arquivo: {backup_path}")
    print("\n2. Agora pode limpar dados de teste:")
    print("   .\\LIMPAR_DADOS_TESTE.bat")
    print("\n3. Começar com dados reais:")
    print("   .\\INICIAR_LOCAL_PROD.bat")
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
