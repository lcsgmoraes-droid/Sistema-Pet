#!/usr/bin/env python3
"""
Script para substituir print() por logger em arquivos Python de produção
Mantém prints em arquivos de teste e scripts utilitários
"""

import os
import re
from pathlib import Path

# Diretórios a processar (produção)
PRODUCTION_DIRS = [
    'backend/app',
]

# Arquivos/diretórios a ignorar
IGNORE_PATTERNS = [
    'test_',
    '_test.py',
    'tests/',
    '__pycache__',
    'migrations/',
    'alembic/',
]

# Mapeamento de padrões de print para logger
REPLACEMENTS = [
    # print("✅ ...") -> logger.info("✅ ...")
    (r'print\((["\'])✅(.*?)\1\)', r'logger.info(\1✅\2\1)'),
    # print("⚠️ ...") -> logger.warning("⚠️ ...")
    (r'print\((["\'])⚠️(.*?)\1\)', r'logger.warning(\1⚠️\2\1)'),
    # print("❌ ...") -> logger.error("❌ ...")
    (r'print\((["\'])❌(.*?)\1\)', r'logger.error(\1❌\2\1)'),
    # print("ERROR:...") -> logger.error("ERROR:...")
    (r'print\((["\'])(?:ERROR|Error|ERRO)(.*?)\1\)', r'logger.error(\1ERROR\2\1)'),
    # print("WARNING:...") -> logger.warning("WARNING:...")
    (r'print\((["\'])(?:WARNING|Warning|AVISO)(.*?)\1\)', r'logger.warning(\1WARNING\2\1)'),
    # print("DEBUG:...") -> logger.debug("DEBUG:...")
    (r'print\((["\'])(?:DEBUG|Debug)(.*?)\1\)', r'logger.debug(\1DEBUG\2\1)'),
    # print(f"...") -> logger.info(f"...")
    (r'print\(f(["\'])(.*?)\1\)', r'logger.info(f\1\2\1)'),
    # print("...") -> logger.info("...")
    (r'print\((["\'])(.*?)\1\)', r'logger.info(\1\2\1)'),
]

def should_ignore(filepath):
    """Verifica se o arquivo deve ser ignorado"""
    filepath_str = str(filepath)
    return any(pattern in filepath_str for pattern in IGNORE_PATTERNS)

def has_logger_import(content):
    """Verifica se o arquivo já importa logger"""
    logger_imports = [
        'from app.core.logger import logger',
        'from core.logger import logger',
        'import logging',
        'logger = logging.getLogger',
    ]
    return any(imp in content for imp in logger_imports)

def add_logger_import(content):
    """Adiciona import do logger se necessário"""
    if has_logger_import(content):
        return content
    
    # Adicionar após os imports existentes
    lines = content.split('\n')
    import_end_idx = 0
    
    for idx, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            import_end_idx = idx
    
    # Adicionar após o último import
    if import_end_idx > 0:
        lines.insert(import_end_idx + 1, 'from app.core.logger import logger')
        return '\n'.join(lines)
    
    # Se não há imports, adicionar no início (após docstring se houver)
    if lines[0].startswith('"""') or lines[0].startswith("'''"):
        # Encontrar fim da docstring
        quote = '"""' if lines[0].startswith('"""') else "'''"
        for idx in range(1, len(lines)):
            if quote in lines[idx]:
                lines.insert(idx + 1, '\nfrom app.core.logger import logger\n')
                return '\n'.join(lines)
    
    # Adicionar no início
    lines.insert(0, 'from app.core.logger import logger\n')
    return '\n'.join(lines)

def replace_prints(content):
    """Substitui prints por logger usando regex"""
    modified = content
    replacements_made = 0
    
    for pattern, replacement in REPLACEMENTS:
        new_content = re.sub(pattern, replacement, modified)
        if new_content != modified:
            replacements_made += re.subn(pattern, replacement, modified)[1]
            modified = new_content
    
    return modified, replacements_made

def process_file(filepath):
    """Processa um único arquivo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Verificar se tem prints
        if 'print(' not in original_content:
            return None
        
        # Substituir prints
        modified_content, count = replace_prints(original_content)
        
        if count == 0:
            return None
        
        # Adicionar import do logger se necessário
        modified_content = add_logger_import(modified_content)
        
        # Salvar arquivo modificado
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        return count
    
    except Exception as e:
        print(f"❌ Erro processando {filepath}: {e}")
        return None

def main():
    """Função principal"""
    print("=" * 80)
    print("🔧 Substituindo print() por logger em arquivos de produção")
    print("=" * 80)
    
    total_files = 0
    total_replacements = 0
    
    for directory in PRODUCTION_DIRS:
        dir_path = Path(directory)
        
        if not dir_path.exists():
            print(f"⚠️  Diretório não encontrado: {directory}")
            continue
        
        print(f"\n📁 Processando: {directory}")
        
        for py_file in dir_path.rglob('*.py'):
            if should_ignore(py_file):
                continue
            
            count = process_file(py_file)
            
            if count:
                total_files += 1
                total_replacements += count
                print(f"  ✅ {py_file.relative_to(dir_path)}: {count} substituições")
    
    print("\n" + "=" * 80)
    print(f"✅ Concluído!")
    print(f"   Arquivos modificados: {total_files}")
    print(f"   Total de substituições: {total_replacements}")
    print("=" * 80)

if __name__ == '__main__':
    main()
