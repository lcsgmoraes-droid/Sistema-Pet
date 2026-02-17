#!/usr/bin/env python3
"""
Script de teste para os endpoints corrigidos
Executa no servidor e mostra logs detalhados
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("TESTANDO ENDPOINTS CORRIGIDOS")
print("=" * 80)

# Endpoint 1: opcoes-filtros (router prefix + app prefix)
print("\n1️⃣ Testando: GET /racoes/analises/opcoes-filtros")
print("-" * 80)

try:
    response = requests.get(f"{BASE_URL}/racoes/analises/opcoes-filtros")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCESSO!")
        print(f"Marcas: {len(data.get('marcas', []))}")
        print(f"Categorias: {len(data.get('categorias', []))}")
        print(f"Espécies: {data.get('especies', [])}")
        print(f"Linhas: {len(data.get('linhas', []))}")
        print(f"Portes: {len(data.get('portes', []))}")
        print(f"Fases: {len(data.get('fases', []))}")
        print(f"Tratamentos: {len(data.get('tratamentos', []))}")
        print(f"Sabores: {data.get('sabores', [])[:5]}...")
        print(f"Pesos: {data.get('pesos', [])[:5]}...")
    elif response.status_code == 401:
        print("\n⚠️ Erro 401 - Autenticação necessária (esperado sem token)")
    else:
        print(f"\n❌ ERRO {response.status_code}")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"\n❌ EXCEÇÃO: {str(e)}")

# Endpoint 2: racao/alertas (router prefix produtos already has /api path in main.py registration)
print("\n\n2️⃣ Testando: GET /produtos/racao/alertas")
print("-" * 80)

try:
    response = requests.get(f"{BASE_URL}/produtos/racao/alertas")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCESSO!")
        print(f"Total: {data.get('total', 0)}")
        print(f"Limite: {data.get('limite', 0)}")
        print(f"Itens retornados: {len(data.get('items', []))}")
        
        if data.get('items'):
            item = data['items'][0]
            print(f"\nPrimeiro item:")
            print(f"  ID: {item.get('id')}")
            print(f"  Nome: {item.get('nome', '')[:50]}")
            print(f"  Completude: {item.get('completude')}%")
            print(f"  Campos faltantes: {item.get('campos_faltantes', [])}")
    elif response.status_code == 401:
        print("\n⚠️ Erro 401 - Autenticação necessária (esperado sem token)")
    else:
        print(f"\n❌ ERRO {response.status_code}")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"\n❌ EXCEÇÃO: {str(e)}")

print("\n" + "=" * 80)
print("FIM DOS TESTES")
print("=" * 80)
