#!/usr/bin/env python3
"""
Script para corrigir imports de models nos arquivos
Remove 'models.' e usa os nomes diretos das classes
"""
import re

files_to_fix = [
    "backend/app/auth_routes_multitenant.py",
    "backend/app/chat_routes.py",
    "backend/app/dre_ia_routes.py",
]

replacements = [
    (r'models\.User\b', 'User'),
    (r'models\.Tenant\b', 'Tenant'),
    (r'models\.Role\b', 'Role'),
    (r'models\.Permission\b', 'Permission'),
    (r'models\.RolePermission\b', 'RolePermission'),
    (r'models\.UserTenant\b', 'UserTenant'),
]

for file_path in files_to_fix:
    print(f"Processando {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ {file_path} atualizado")
        else:
            print(f"  ⏭️  {file_path} sem alterações")
            
    except FileNotFoundError:
        print(f"  ❌ Arquivo não encontrado: {file_path}")
    except Exception as e:
        print(f"  ❌ Erro ao processar {file_path}: {e}")

print("\n✅ Correção de imports concluída!")
