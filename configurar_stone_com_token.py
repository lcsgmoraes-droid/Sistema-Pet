"""
Configura Stone usando token fornecido
Uso: python configurar_stone_com_token.py <seu_token_jwt>
"""

import sys
import requests
import json

BASE_URL = "http://localhost:8000"

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

if len(sys.argv) < 2:
    print()
    print("❌ Token não fornecido!")
    print()
    print("Uso:")
    print(f"   python {sys.argv[0]} <seu_token_jwt>")
    print()
    print("Como obter o token:")
    print("1. Acesse: http://localhost:8000/docs")
    print("2. Expanda POST /auth/login")
    print("3. Clique em 'Try it out'")
    print("4. Insira suas credenciais:")
    print('   {"username": "admin", "password": "admin123"}')
    print("5. Clique em 'Execute'")
    print("6. Copie o 'access_token' da resposta")
    print("7. Execute este script novamente")
    print()
    sys.exit(1)

token = sys.argv[1]

print()
print("="*60)
print("🔧 CONFIGURANDO STONE VIA API")
print("="*60)
print()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("📤 Enviando configuração Stone...")
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
    print("📊 Configuração salva:")
    config = data.get('config', {})
    print(f"   ID: {config.get('id')}")
    print(f"   Merchant ID: {config.get('merchant_id')}")
    print(f"   Ambiente: {'SANDBOX' if config.get('sandbox') else 'PRODUÇÃO'}")
    print(f"   PIX: {'✅' if config.get('enable_pix') else '❌'}")
    print(f"   Cartão Crédito: {'✅' if config.get('enable_credit_card') else '❌'}")
    print(f"   Cartão Débito: {'✅' if config.get('enable_debit_card') else '❌'}")
    print(f"   Parcelas: Até {config.get('max_installments')}x")
    print()
    print("="*60)
    print("✅ PRONTO PARA PROCESSAR PAGAMENTOS!")
    print("="*60)
    print()
    print("🎯 Teste agora:")
    print()
    print("1. Criar pagamento PIX:")
    print('   curl -X POST http://localhost:8000/api/stone/payments/pix \\')
    print(f'        -H "Authorization: Bearer {token[:20]}..." \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"amount": 10.50, "description": "Teste", "external_id": "teste-001"}\'')
    print()
    print("2. Ou acesse a documentação interativa:")
    print("   http://localhost:8000/docs")
    print("   Procure por 'Stone - Pagamentos PIX e Cartão'")
    print()
    
elif response.status_code == 401:
    print("❌ Token inválido ou expirado!")
    print("   Faça login novamente em http://localhost:8000/docs")
    print()
    
else:
    print(f"❌ Erro ao configurar Stone (Status {response.status_code})")
    print()
    try:
        error = response.json()
        print("Detalhes:")
        print(json.dumps(error, indent=2))
    except:
        print(response.text)
    print()
