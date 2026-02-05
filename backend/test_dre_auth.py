"""
Teste dos novos endpoints de DRE Detalhada por Canal
Com autenticação
"""

import requests
import json
from datetime import date

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("TESTE - DRE DETALHADA POR CANAL")
print("=" * 60)

# 1. Login
print("\n[LOGIN] Fazendo login...")
try:
    login_payload = {
        "email": "admin@test.com",
        "password": "123456"
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    if response.status_code == 200:
        token_data = response.json()
        token = token_data.get('access_token')
        print(f"OK Login realizado!")
        print(f"   Token: {token[:20]}...")
    else:
        print(f"ERRO no login: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"ERRO: {e}")
    exit(1)

# Headers com autenticação
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

data_inicio = date(2024, 11, 1)
data_fim = date(2024, 11, 30)

# 2. Listar canais
print("\n[1] Listando canais disponíveis...")
try:
    response = requests.get(f"{BASE_URL}/api/ia/dre/canais", headers=headers)
    if response.status_code == 200:
        canais = response.json()
        print(f"OK Canais:")
        for canal in canais.get('canais', []):
            print(f"   - {canal.get('nome')} ({canal.get('key')})")
    else:
        print(f"ERRO: {response.status_code} - {response.text}")
except Exception as e:
    print(f"ERRO: {e}")

# 3. Calcular DRE de um canal específico
print("\n[2] Calculando DRE do Loja Física...")
try:
    payload = {
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "canal": "loja_fisica"
    }
    response = requests.post(f"{BASE_URL}/api/ia/dre/calcular-detalhado", json=payload, headers=headers)
    if response.status_code == 200:
        dre = response.json()
        print(f"OK DRE Loja Física:")
        print(f"   Receita Bruta: R$ {dre.get('receita_bruta', 0):,.2f}")
        print(f"   Receita Líquida: R$ {dre.get('receita_liquida', 0):,.2f}")
        print(f"   Lucro Líquido: R$ {dre.get('lucro_liquido', 0):,.2f}")
        print(f"   Margem: {dre.get('margem_liquida_percent', 0):.2f}%")
        print(f"   Status: {dre.get('status', 'N/A')}")
    else:
        print(f"ERRO: {response.status_code}")
        print(f"   Resposta: {response.text}")
except Exception as e:
    print(f"ERRO: {e}")

# 4. Alocar despesa proporcional
print("\n[3] Alocando despesa proporcional...")
try:
    payload = {
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "categoria": "aluguel",
        "valor_total": 7000,
        "modo": "proporcional",
        "canais": ["loja_fisica", "mercado_livre"],
        "usar_faturamento": True
    }
    response = requests.post(f"{BASE_URL}/api/ia/dre/alocar-despesa", json=payload, headers=headers)
    if response.status_code == 200:
        resultado = response.json()
        print(f"OK Despesa alocada:")
        print(f"   Mensagem: {resultado.get('mensagem')}")
        print(f"   Modo: {resultado.get('modo')}")
    else:
        print(f"ERRO: {response.status_code}")
        print(f"   Resposta: {response.text}")
except Exception as e:
    print(f"ERRO: {e}")

# 5. Alocar despesa manual
print("\n[4] Alocando despesa manual...")
try:
    payload = {
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "categoria": "marketing",
        "valor_total": 3000,
        "modo": "manual",
        "canais": ["mercado_livre", "shopee"],
        "usar_faturamento": False,
        "alocacao_manual": {
            "mercado_livre": {"valor": 1800, "percentual": 60},
            "shopee": {"valor": 1200, "percentual": 40}
        }
    }
    response = requests.post(f"{BASE_URL}/api/ia/dre/alocar-despesa", json=payload, headers=headers)
    if response.status_code == 200:
        resultado = response.json()
        print(f"OK Despesa alocada manualmente:")
        print(f"   Mensagem: {resultado.get('mensagem')}")
    else:
        print(f"ERRO: {response.status_code}")
        print(f"   Resposta: {response.text}")
except Exception as e:
    print(f"ERRO: {e}")

# 6. Consolidar DRE de múltiplos canais
print("\n[5] Consolidando DRE de múltiplos canais...")
try:
    payload = {
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "canais": ["loja_fisica", "mercado_livre", "shopee"]
    }
    response = requests.post(f"{BASE_URL}/api/ia/dre/consolidado", json=payload, headers=headers)
    if response.status_code == 200:
        dre = response.json()
        print(f"OK DRE Consolidado:")
        print(f"\n   RECEITAS:")
        for r in dre.get('receitas', {}).get('detalhado', []):
            print(f"     - {r.get('canal_nome')}: R$ {r.get('receita_liquida', 0):,.2f}")
        print(f"     TOTAL: R$ {dre.get('receitas', {}).get('totais', {}).get('receita_liquida', 0):,.2f}")
        
        print(f"\n   CONSOLIDADO:")
        cons = dre.get('consolidado', {})
        print(f"     Lucro Operacional: R$ {cons.get('lucro_operacional', 0):,.2f}")
        print(f"     Impostos: R$ {cons.get('impostos', 0):,.2f}")
        print(f"     Lucro Líquido: R$ {cons.get('lucro_liquido', 0):,.2f}")
        print(f"     Margem: {cons.get('margem_liquida_percent', 0):.2f}%")
        print(f"     Status: {cons.get('status', 'N/A')}")
    else:
        print(f"ERRO: {response.status_code}")
        print(f"   Resposta: {response.text}")
except Exception as e:
    print(f"ERRO: {e}")

print("\n" + "=" * 60)
print("✅ TESTES CONCLUÍDOS!")
print("=" * 60)
