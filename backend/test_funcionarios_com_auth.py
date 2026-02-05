import requests
import json

# Fazer login primeiro para obter token
login_url = "http://localhost:8000/login"
login_data = {
    "username": "admin",
    "password": "admin123"
}

print("=" * 80)
print("1. FAZENDO LOGIN...")
print("=" * 80)
response = requests.post(login_url, json=login_data)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    token = response.json().get("access_token")
    print(f"Token obtido: {token[:50]}...")
    
    # Testar endpoint de funcionários
    print("\n" + "=" * 80)
    print("2. TESTANDO /comissoes/funcionarios COM TOKEN")
    print("=" * 80)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    funcionarios_url = "http://localhost:8000/comissoes/funcionarios"
    response = requests.get(funcionarios_url, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
else:
    print(f"Erro no login: {response.text}")
