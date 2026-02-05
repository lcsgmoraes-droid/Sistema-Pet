import requests
import json

# Configurar token (substitua pelo token válido)
TOKEN = "seu_token_aqui"  # Execute primeiro: criar_admin.py para obter token

BASE_URL = "http://127.0.0.1:8000"

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

# Dados da devolução
payload = {
    'caixa_id': None,
    'gerar_credito': True,
    'motivo': 'Teste de devolução com crédito',
    'itens': [
        {
            'item_id': 254,  # ID do item da venda 95
            'quantidade': 1
        }
    ]
}

print("🔄 Testando devolução com crédito...")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(
        f'{BASE_URL}/vendas/95/devolucao',
        headers=headers,
        json=payload,
        timeout=10
    )
    
    print(f"\n📊 Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ Devolução realizada com sucesso!")
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"\n❌ Erro na devolução!")
        
except requests.exceptions.RequestException as e:
    print(f"\n🚨 Erro na requisição: {e}")
