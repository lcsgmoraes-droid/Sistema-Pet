"""
Teste dos novos endpoints de DRE Detalhada por Canal
"""

import requests
import json
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000/api/ia/dre"

# Dados de teste
TEST_USER_ID = 1
data_inicio = date(2024, 11, 1)
data_fim = date(2024, 11, 30)

print("=" * 60)
print("TESTE - DRE DETALHADA POR CANAL")
print("=" * 60)

# 1. Listar canais
print("\n1️⃣  Listando canais disponíveis...")
try:
    response = requests.get(f"{BASE_URL}/canais")
    if response.status_code == 200:
        canais = response.json()
        print(f"✅ Canais: {json.dumps(canais, indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ Erro: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Erro: {e}")

# 2. Calcular DRE de um canal específico
print("\n2️⃣  Calculando DRE do Loja Física...")
try:
    payload = {
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "canal": "loja_fisica"
    }
    response = requests.post(f"{BASE_URL}/calcular-detalhado", json=payload)
    if response.status_code == 200:
        dre = response.json()
        print(f"✅ DRE Loja Física:")
        print(f"   Receita Bruta: R$ {dre.get('receita_bruta', 0):,.2f}")
        print(f"   Receita Líquida: R$ {dre.get('receita_liquida', 0):,.2f}")
        print(f"   Lucro Líquido: R$ {dre.get('lucro_liquido', 0):,.2f}")
        print(f"   Margem: {dre.get('margem_liquida_percent', 0):.2f}%")
        print(f"   Status: {dre.get('status', 'N/A')}")
    else:
        print(f"❌ Erro: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Erro: {e}")

# 3. Aalocar despesa proporcional
print("\n3️⃣  Alocando despesa proporcional...")
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
    response = requests.post(f"{BASE_URL}/alocar-despesa", json=payload)
    if response.status_code == 200:
        resultado = response.json()
        print(f"✅ Despesa alocada:")
        print(f"   Categoria: {resultado.get('categoria', 'N/A')}")
        print(f"   Modo: {resultado.get('modo', 'N/A')}")
        print(f"   Canais: {resultado.get('canais', [])}")
    else:
        print(f"❌ Erro: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Erro: {e}")

# 4. Aalocar despesa manual
print("\n4️⃣  Alocando despesa manual...")
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
    response = requests.post(f"{BASE_URL}/alocar-despesa", json=payload)
    if response.status_code == 200:
        resultado = response.json()
        print(f"✅ Despesa alocada manualmente:")
        print(f"   Categoria: {resultado.get('categoria', 'N/A')}")
        print(f"   Modo: {resultado.get('modo', 'N/A')}")
    else:
        print(f"❌ Erro: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Erro: {e}")

# 5. Consolidar DRE de múltiplos canais
print("\n5️⃣  Consolidando DRE de múltiplos canais...")
try:
    payload = {
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "canais": ["loja_fisica", "mercado_livre", "shopee"]
    }
    response = requests.post(f"{BASE_URL}/consolidado", json=payload)
    if response.status_code == 200:
        dre = response.json()
        print(f"✅ DRE Consolidado:")
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
        print(f"❌ Erro: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n" + "=" * 60)
print("✅ TESTES CONCLUÍDOS!")
print("=" * 60)
