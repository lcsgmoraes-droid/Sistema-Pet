"""
TESTE DOS ENDPOINTS ABA 5

Script para testar os endpoints da ABA 5 - Fluxo de Caixa Preditivo

Execute com:
    python test_aba5_endpoints.py
    
Ou use a documentação Swagger:
    http://localhost:8000/docs (GET /docs)
"""

import requests
import json
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

BASE_URL = "http://localhost:8000"

# USUARIO ID (ajuste conforme necessário)
USUARIO_ID = 1

# Token (você precisa fazer login primeiro)
# Exemplo: POST /auth/login com usuario/senha
TOKEN = ""

# Headers
HEADERS = {
    "Authorization": f"Bearer {TOKEN}" if TOKEN else None,
    "Content-Type": "application/json"
}

def clean_headers():
    """Remove header None"""
    return {k: v for k, v in HEADERS.items() if v}

# ============================================================================
# TESTE 1: HEALTH CHECK
# ============================================================================

def test_health_check():
    """Verifica se o módulo IA está funcional"""
    print("\n" + "="*70)
    print("TEST 1: Health Check")
    print("="*70)
    
    url = f"{BASE_URL}/api/ia/fluxo/health"
    
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASSOU")
        else:
            print("❌ FALHOU")
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")


# ============================================================================
# TESTE 2: GET ÍNDICES DE SAÚDE
# ============================================================================

def test_get_indices_saude():
    """Obtém índices de saúde do caixa"""
    print("\n" + "="*70)
    print("TEST 2: Get Índices de Saúde")
    print("="*70)
    
    url = f"{BASE_URL}/api/ia/fluxo/indices-saude/{USUARIO_ID}"
    
    try:
        response = requests.get(url, headers=clean_headers())
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASSOU")
        else:
            print("❌ FALHOU")
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")


# ============================================================================
# TESTE 3: GET PROJEÇÕES
# ============================================================================

def test_get_projecoes():
    """Obtém projeções já calculadas"""
    print("\n" + "="*70)
    print("TEST 3: Get Projeções (15 dias)")
    print("="*70)
    
    url = f"{BASE_URL}/api/ia/fluxo/projecoes/{USUARIO_ID}?dias=15"
    
    try:
        response = requests.get(url, headers=clean_headers())
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total de projeções: {len(data)}")
        if data:
            print(f"Primeira projeção: {json.dumps(data[0], indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASSOU")
        else:
            print("❌ FALHOU")
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")


# ============================================================================
# TESTE 4: POST PROJETAR 15 DIAS
# ============================================================================

def test_post_projetar_15_dias():
    """Gera nova projeção com Prophet"""
    print("\n" + "="*70)
    print("TEST 4: Post Projetar 15 Dias (PROPHET)")
    print("="*70)
    
    url = f"{BASE_URL}/api/ia/fluxo/projetar-15-dias/{USUARIO_ID}"
    
    try:
        response = requests.post(url, headers=clean_headers())
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total de projeções: {len(data) if isinstance(data, list) else 'erro'}")
        if isinstance(data, list) and data:
            print(f"Primeira: {json.dumps(data[0], indent=2)}")
        else:
            print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASSOU")
        else:
            print("❌ FALHOU")
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")


# ============================================================================
# TESTE 5: GET ALERTAS
# ============================================================================

def test_get_alertas():
    """Obtém alertas gerados"""
    print("\n" + "="*70)
    print("TEST 5: Get Alertas")
    print("="*70)
    
    url = f"{BASE_URL}/api/ia/fluxo/alertas/{USUARIO_ID}"
    
    try:
        response = requests.get(url, headers=clean_headers())
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total de alertas: {len(data) if isinstance(data, list) else 0}")
        for i, alerta in enumerate(data if isinstance(data, list) else []):
            print(f"\n  Alerta {i+1}:")
            print(f"    Tipo: {alerta.get('tipo')}")
            print(f"    Título: {alerta.get('titulo')}")
            print(f"    Mensagem: {alerta.get('mensagem')}")
        
        if response.status_code == 200:
            print("\n✅ PASSOU")
        else:
            print("\n❌ FALHOU")
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")


# ============================================================================
# TESTE 6: POST SIMULAR CENÁRIO
# ============================================================================

def test_post_simular_cenario():
    """Simula cenário"""
    print("\n" + "="*70)
    print("TEST 6: Post Simular Cenário (OTIMISTA)")
    print("="*70)
    
    url = f"{BASE_URL}/api/ia/fluxo/simular-cenario/{USUARIO_ID}"
    
    payload = {
        "cenario": "otimista"
    }
    
    try:
        response = requests.post(url, json=payload, headers=clean_headers())
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if 'cenario' in data:
            print(f"Cenário: {data.get('cenario')}")
            projecoes = data.get('projecoes_ajustadas', [])
            print(f"Total de projeções: {len(projecoes)}")
            if projecoes:
                print(f"Primeira: {json.dumps(projecoes[0], indent=2)}")
        else:
            print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASSOU")
        else:
            print("❌ FALHOU")
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")


# ============================================================================
# TESTE 7: POST REGISTRAR MOVIMENTAÇÃO
# ============================================================================

def test_post_registrar_movimentacao():
    """Registra movimentação manual"""
    print("\n" + "="*70)
    print("TEST 7: Post Registrar Movimentação")
    print("="*70)
    
    url = f"{BASE_URL}/api/ia/fluxo/registrar-movimentacao/{USUARIO_ID}"
    
    payload = {
        "tipo": "receita",
        "categoria": "Venda PDV",
        "valor": 1500.00,
        "descricao": "Teste de movimentação",
        "data_prevista": (datetime.utcnow() + timedelta(days=1)).isoformat()
    }
    
    try:
        response = requests.post(url, json=payload, headers=clean_headers())
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASSOU")
        else:
            print("❌ FALHOU")
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")


# ============================================================================
# EXECUTAR TESTES
# ============================================================================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                  TESTE DOS ENDPOINTS ABA 5                                ║
║          Fluxo de Caixa Preditivo - Sistema Pet Shop Pro                  ║
╚════════════════════════════════════════════════════════════════════════════╝

⚠️  IMPORTANTE: 
  - Certifique que o backend está rodando: python -m uvicorn app.main:app --reload
  - Se os testes falharem com 403, você precisa de um TOKEN de autenticação
  - Para gerar token: POST /auth/login com suas credenciais

""")
    
    # Executar testes
    test_health_check()
    test_get_indices_saude()
    test_get_projecoes()
    test_post_registrar_movimentacao()
    test_post_projetar_15_dias()
    test_get_alertas()
    test_post_simular_cenario()
    
    print("\n" + "="*70)
    print("✅ TESTES CONCLUÍDOS")
    print("="*70)
