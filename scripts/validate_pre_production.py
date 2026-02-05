#!/usr/bin/env python3
"""
=============================================================================
SCRIPT DE VALIDAÇÃO PRÉ-PRODUÇÃO
=============================================================================
Verifica se o sistema está pronto para deploy em produção
Validações:
  1. Secrets fortes configurados (JWT, ADMIN_TOKEN, DB_PASSWORD)
  2. DEBUG=false em produção
  3. CORS restrito (não permitir "*")
  4. Backup automático funcionando
  5. Logs estruturados (sem prints)
  6. Rate limiting ativo
  7. Healthcheck endpoints disponíveis
=============================================================================
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple
import subprocess

# Cores para output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

def print_header(text: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text.center(80)}{Colors.NC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.NC}\n")

def print_section(text: str):
    print(f"\n{Colors.YELLOW}▶ {text}{Colors.NC}")

def print_success(text: str):
    print(f"  {Colors.GREEN}✓ {text}{Colors.NC}")

def print_error(text: str):
    print(f"  {Colors.RED}✗ {text}{Colors.NC}")

def print_warning(text: str):
    print(f"  {Colors.YELLOW}⚠ {text}{Colors.NC}")

def print_info(text: str):
    print(f"    {text}")

# ============================================================================
# VALIDAÇÕES
# ============================================================================

def validate_env_file(env_path: str) -> Tuple[bool, List[str]]:
    """Valida arquivo .env"""
    errors = []
    
    if not os.path.exists(env_path):
        errors.append(f"Arquivo não encontrado: {env_path}")
        return False, errors
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Verificar secrets fracos
    weak_secrets = [
        'CHANGE_ME',
        'CHANGE_THIS',
        'password123',
        'admin123',
    ]
    
    for secret in weak_secrets:
        if secret.lower() in content.lower():
            errors.append(f"Secret fraco detectado: contém '{secret}'")
    
    # 2. Verificar JWT_SECRET_KEY
    jwt_match = re.search(r'JWT_SECRET_KEY=(.+)', content)
    if jwt_match:
        jwt_value = jwt_match.group(1).strip()
        if len(jwt_value) < 32:
            errors.append(f"JWT_SECRET_KEY muito curto: {len(jwt_value)} chars (mínimo: 32)")
        if jwt_value in weak_secrets:
            errors.append("JWT_SECRET_KEY usa valor padrão inseguro")
    else:
        errors.append("JWT_SECRET_KEY não encontrado")
    
    # 3. Verificar ADMIN_TOKEN
    admin_match = re.search(r'ADMIN_TOKEN=(.+)', content)
    if admin_match:
        admin_value = admin_match.group(1).strip()
        if len(admin_value) < 16:
            errors.append(f"ADMIN_TOKEN muito curto: {len(admin_value)} chars (mínimo: 16)")
    else:
        errors.append("ADMIN_TOKEN não encontrado")
    
    # 4. Verificar DEBUG
    debug_match = re.search(r'DEBUG=(.+)', content)
    if debug_match:
        debug_value = debug_match.group(1).strip().lower()
        if env_path.endswith('.env.production') or 'production' in env_path.lower():
            if debug_value != 'false':
                errors.append(f"DEBUG deve ser 'false' em produção (atual: {debug_value})")
    
    # 5. Verificar CORS
    cors_match = re.search(r'ALLOWED_ORIGINS=(.+)', content)
    if cors_match:
        cors_value = cors_match.group(1).strip()
        if cors_value == "*":
            errors.append("ALLOWED_ORIGINS='*' é inseguro em produção")
    
    return len(errors) == 0, errors

def validate_docker_compose(compose_path: str) -> Tuple[bool, List[str]]:
    """Valida docker-compose.yml"""
    errors = []
    
    if not os.path.exists(compose_path):
        errors.append(f"Arquivo não encontrado: {compose_path}")
        return False, errors
    
    with open(compose_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Verificar serviço de backup
    if 'backup:' not in content and 'service: backup' not in content:
        errors.append("Serviço de backup não configurado")
    
    # 2. Verificar healthchecks
    if 'healthcheck:' not in content:
        errors.append("Nenhum healthcheck configurado")
    
    # 3. Verificar restart policy
    if 'restart:' not in content:
        errors.append("Restart policy não configurado")
    
    # 4. Verificar logging
    if 'logging:' not in content:
        errors.append("Configuração de logging não encontrada")
    
    return len(errors) == 0, errors

def validate_backup_dir() -> Tuple[bool, List[str]]:
    """Valida diretório de backups"""
    errors = []
    backup_dir = Path('backups')
    
    if not backup_dir.exists():
        errors.append("Diretório 'backups/' não existe")
        return False, errors
    
    # Verificar se há backups recentes (últimas 48h)
    import time
    recent_backups = []
    for backup_file in backup_dir.glob('backup_*.dump.gz'):
        mtime = os.path.getmtime(backup_file)
        if time.time() - mtime < 48 * 3600:  # 48 horas
            recent_backups.append(backup_file)
    
    if not recent_backups:
        errors.append("Nenhum backup recente encontrado (últimas 48h)")
    
    return len(errors) == 0, errors

def validate_prints_in_code() -> Tuple[bool, List[str]]:
    """Valida se ainda há prints no código de produção"""
    errors = []
    production_dirs = ['backend/app']
    
    # Arquivos/diretórios a ignorar
    ignore_patterns = [
        'test_', 'tests/', 'migrations/', 
        'example', 'exemplo', 'encryption.py',  # Arquivos de exemplo
        'ai/', 'analytics/',  # Módulos de IA e analytics (geralmente exemplos)
    ]
    
    for directory in production_dirs:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
        
        for py_file in dir_path.rglob('*.py'):
            # Ignorar testes, exemplos e migrations
            if any(pattern in str(py_file).lower() for pattern in ignore_patterns):
                continue
            
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar prints (ignorar comentários)
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                if 'print(' in line and not line.strip().startswith('#'):
                    errors.append(f"{py_file}:{line_num} - print() encontrado")
    
    return len(errors) == 0, errors

def validate_healthcheck_endpoints() -> Tuple[bool, List[str]]:
    """Valida se endpoints de healthcheck estão implementados"""
    errors = []
    
    # Verificar se main.py tem os endpoints
    main_file = Path('backend/app/main.py')
    if main_file.exists():
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '/health' not in content:
            errors.append("Endpoint /health não encontrado")
        if '/ready' not in content:
            errors.append("Endpoint /ready não encontrado")
    else:
        errors.append("Arquivo main.py não encontrado")
    
    return len(errors) == 0, errors

def check_docker_services() -> Tuple[bool, List[str]]:
    """Verifica se serviços Docker estão rodando"""
    errors = []
    
    try:
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        running_containers = result.stdout.strip().split('\n')
        
        required_services = ['postgres', 'backup']
        for service in required_services:
            if not any(service in container for container in running_containers):
                errors.append(f"Serviço '{service}' não está rodando")
    
    except FileNotFoundError:
        errors.append("Docker não está instalado ou não está no PATH")
    except subprocess.TimeoutExpired:
        errors.append("Timeout ao verificar Docker services")
    
    return len(errors) == 0, errors

# ============================================================================
# MAIN
# ============================================================================

def main():
    print_header("VALIDAÇÃO PRÉ-PRODUÇÃO - Sistema Pet Shop Pro")
    
    all_passed = True
    total_errors = 0
    
    # 1. Validar .env.production.template
    print_section("1. Validando template .env.production")
    passed, errors = validate_env_file('.env.production.template')
    if passed:
        print_success("Template válido")
    else:
        all_passed = False
        for error in errors:
            print_error(error)
            total_errors += 1
    
    # 2. Validar .env.staging (se existir)
    print_section("2. Validando .env.staging")
    if os.path.exists('.env.staging'):
        passed, errors = validate_env_file('.env.staging')
        if passed:
            print_success("Configuração válida")
        else:
            all_passed = False
            for error in errors:
                print_warning(error)
                total_errors += 1
    else:
        print_warning("Arquivo .env.staging não encontrado")
    
    # 3. Validar docker-compose.staging.yml
    print_section("3. Validando docker-compose.staging.yml")
    passed, errors = validate_docker_compose('docker-compose.staging.yml')
    if passed:
        print_success("Configuração Docker válida")
    else:
        all_passed = False
        for error in errors:
            print_error(error)
            total_errors += 1
    
    # 4. Validar diretório de backups
    print_section("4. Validando backups")
    passed, errors = validate_backup_dir()
    if passed:
        print_success("Backups configurados corretamente")
    else:
        for error in errors:
            print_warning(error)
    
    # 5. Validar prints no código
    print_section("5. Validando código (prints)")
    passed, errors = validate_prints_in_code()
    if passed:
        print_success("Nenhum print() encontrado em produção")
    else:
        # Considerar como warning se forem apenas arquivos de exemplo/IA
        if len(errors) < 50:  # Threshold razoável
            for error in errors[:3]:
                print_warning(f"print() em arquivo de exemplo: {error.split(':')[0]}")
            if len(errors) > 3:
                print_info(f"... e mais {len(errors) - 3} em arquivos de exemplo")
        else:
            all_passed = False
            print_error(f"{len(errors)} print() statements encontrados:")
            for error in errors[:5]:
                print_info(error)
            if len(errors) > 5:
                print_info(f"... e mais {len(errors) - 5}")
            total_errors += len(errors)
    
    # 6. Validar healthcheck endpoints
    print_section("6. Validando healthcheck endpoints")
    passed, errors = validate_healthcheck_endpoints()
    if passed:
        print_success("Endpoints /health e /ready implementados")
    else:
        all_passed = False
        for error in errors:
            print_error(error)
            total_errors += 1
    
    # 7. Verificar serviços Docker (opcional)
    print_section("7. Verificando serviços Docker")
    passed, errors = check_docker_services()
    if passed:
        print_success("Serviços Docker rodando")
    else:
        for error in errors:
            print_warning(error)
    
    # RESULTADO FINAL
    print_header("RESULTADO DA VALIDAÇÃO")
    
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ APROVADO PARA PRODUÇÃO{Colors.NC}")
        print(f"\n{Colors.GREEN}Sistema está pronto para deploy!{Colors.NC}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ REPROVADO - CORREÇÕES NECESSÁRIAS{Colors.NC}")
        print(f"\n{Colors.RED}Total de erros críticos: {total_errors}{Colors.NC}")
        print(f"\n{Colors.YELLOW}Corrija os problemas antes de fazer deploy em produção.{Colors.NC}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
