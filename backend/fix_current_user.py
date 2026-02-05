#!/usr/bin/env python3
"""
Script para corrigir current_user.id para user.id em notas_entrada_routes.py
"""
import re

# Ler o arquivo
with open('/app/app/notas_entrada_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Substituir current_user.id por user.id
content = content.replace('current_user.id', 'user.id')

# Salvar
with open('/app/app/notas_entrada_routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Arquivo corrigido! Substituídas todas as ocorrências de 'current_user.id' por 'user.id'")
