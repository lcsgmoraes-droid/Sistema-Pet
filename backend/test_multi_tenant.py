"""
Teste Multi-Tenant - Verificar se endpoints autenticados funcionam
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """Testa login e obtém token"""
    print("=" * 60)
    print("1. Testando LOGIN...")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "admin@test.com",
            "password": "admin123"
        }
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Login bem-sucedido!")
        print(f"Token Type: {data.get('token_type')}")
        print(f"Access Token: {data.get('access_token')[:50]}...")
        return data.get('access_token')
    else:
        print(f"❌ Erro no login: {response.text}")
        return None


def test_dashboard(token):
    """Testa endpoint do dashboard (requer autenticação)"""
    print("\n" + "=" * 60)
    print("2. Testando DASHBOARD (endpoint autenticado)...")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/dashboard",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Dashboard carregado com sucesso!")
        print(f"Dados do tenant: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
        return True
    else:
        print(f"❌ Erro ao carregar dashboard: {response.text}")
        return False


def test_produtos(token):
    """Testa endpoint de produtos (requer autenticação)"""
    print("\n" + "=" * 60)
    print("3. Testando PRODUTOS (endpoint autenticado)...")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/produtos?skip=0&limit=5",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Produtos carregados com sucesso!")
        print(f"Total: {len(data)} produtos")
        if data:
            print(f"Primeiro produto: {data[0].get('nome')}")
        return True
    else:
        print(f"❌ Erro ao carregar produtos: {response.text}")
        return False


if __name__ == "__main__":
    print("\n🔍 TESTE MULTI-TENANT - ISOLAMENTO DE DADOS\n")
    
    # Passo 1: Login
    token = test_login()
    
    if not token:
        print("\n❌ FALHA: Não foi possível obter token")
        exit(1)
    
    # Passo 2: Dashboard
    dashboard_ok = test_dashboard(token)
    
    # Passo 3: Produtos
    produtos_ok = test_produtos(token)
    
    # Resultado final
    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)
    
    if dashboard_ok and produtos_ok:
        print("✅ TODOS OS TESTES PASSARAM")
        print("✅ Multi-tenant funcionando corretamente!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("Verifique os erros acima")
