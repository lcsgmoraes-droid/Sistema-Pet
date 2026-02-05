"""
Configura Stone via API no backend rodando
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Credenciais Stone
STONE_CONFIG = {
    "client_id": "sk_83973c1ff4674497bade8bd2bf8856da",
    "client_secret": "sk_83973c1ff4674497bade8bd2bf8856da",
    "merchant_id": "128845743",
    "webhook_secret": "",
    "sandbox": True,
    "enable_pix": True,
    "enable_credit_card": True,
    "enable_debit_card": False,
    "max_installments": 12,
    "webhook_url": "https://seu-dominio.com/api/stone/webhook"
}

def fazer_login():
    """Faz login e retorna o token"""
    print("🔐 Fazendo login com admin@test.com...")
    
    # Login multitenant - Fase 1: Obter tenants
    try:
        response = requests.post(
            f"{BASE_URL}/login-multitenant",
            json={
                "email": "admin@test.com",
                "password": "test123"
            }
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login fase 1 realizado!")
            
            # Pega primeiro tenant
            tenants = data.get("tenants", [])
            if not tenants:
                print("❌ Nenhum tenant encontrado")
                return None
            
            tenant = tenants[0]
            print(f"   Tenant: {tenant.get('nome')} (ID: {tenant.get('id')})")
            
            # Fase 2: Selecionar tenant
            print("\n🔐 Selecionando tenant...")
            response2 = requests.post(
                f"{BASE_URL}/select-tenant",
                json={
                    "email": "admin@test.com",
                    "tenant_id": tenant.get("id")
                }
            )
            
            print(f"   Status: {response2.status_code}")
            
            if response2.status_code == 200:
                data2 = response2.json()
                token = data2.get("access_token")
                if token:
                    print(f"✅ Token obtido com sucesso!")
                    return token
            else:
                print(f"   Erro fase 2: {response2.text[:200]}")
        else:
            print(f"   Erro fase 1: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
    
    print("❌ Não foi possível fazer login automaticamente")
    print()
    print("Por favor, faça login manualmente:")
    print("1. Acesse: http://localhost:8000/docs")
    print("2. Faça login em POST /auth/login")
    print("3. Copie o access_token")
    print("4. Execute: configurar_stone_com_token.py <token>")
    return None


def configurar_stone(token):
    """Configura Stone via API"""
    print()
    print("="*60)
    print("🔧 CONFIGURANDO STONE VIA API")
    print("="*60)
    print()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Tenta configurar
    print("📤 Enviando configuração...")
    response = requests.post(
        f"{BASE_URL}/api/stone/config",
        headers=headers,
        json=STONE_CONFIG
    )
    
    print(f"   Status: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        print("✅ STONE CONFIGURADA COM SUCESSO!")
        print()
        print("📊 Configuração:")
        print(f"   Client ID: {STONE_CONFIG['client_id'][:20]}...")
        print(f"   Merchant ID: {STONE_CONFIG['merchant_id']}")
        print(f"   Ambiente: {'SANDBOX (Testes)' if STONE_CONFIG['sandbox'] else 'PRODUÇÃO'}")
        print(f"   PIX: {'Ativado' if STONE_CONFIG['enable_pix'] else 'Desativado'}")
        print(f"   Cartão Crédito: {'Ativado' if STONE_CONFIG['enable_credit_card'] else 'Desativado'}")
        print(f"   Parcelas: Até {STONE_CONFIG['max_installments']}x")
        print()
        print("="*60)
        print("✅ PRONTO PARA USAR!")
        print("="*60)
        print()
        print("🎯 Próximos passos:")
        print("1. Teste criar um PIX:")
        print("   POST http://localhost:8000/api/stone/payments/pix")
        print()
        print("2. Acesse a documentação:")
        print("   http://localhost:8000/docs")
        print()
        print("3. Veja os endpoints Stone em 'Stone - Pagamentos PIX e Cartão'")
        print()
        return True
    else:
        print("❌ Erro ao configurar Stone")
        print()
        try:
            error = response.json()
            print("Detalhes do erro:")
            print(json.dumps(error, indent=2))
        except:
            print(response.text)
        print()
        return False


def main():
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║       CONFIGURAÇÃO STONE - BACKEND RODANDO                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # Verifica se backend está rodando
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend não está respondendo corretamente")
            print("   Inicie com: docker compose -f docker-compose.staging.yml up -d")
            return
    except Exception as e:
        print("❌ Backend não está acessível em http://localhost:8000")
        print("   Inicie com: docker compose -f docker-compose.staging.yml up -d")
        return
    
    print("✅ Backend rodando em http://localhost:8000")
    print()
    
    # Faz login
    token = fazer_login()
    
    if not token:
        return
    
    # Configura Stone
    configurar_stone(token)


if __name__ == "__main__":
    main()
    print()
