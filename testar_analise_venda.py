import requests
import json

# Dados de teste
payload = {
    "items": [
        {
            "produto_id": 1,
            "preco_venda": 100.0,
            "quantidade": 1,
            "custo": None
        }
    ],
    "desconto": 0,
    "taxa_entrega": 0,
    "formas_pagamento": [
        {
            "forma_pagamento_id": 1,
            "valor": 100.0,
            "parcelas": 1
        }
    ]
}

try:
    response = requests.post(
        "http://127.0.0.1:8000/formas-pagamento/analisar-venda",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"\nResponse:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"Erro: {e}")
    if hasattr(e, 'response'):
        print(f"Response text: {e.response.text}")
