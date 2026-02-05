import requests

# Token do usuário admin (você precisa fazer login primeiro para pegar o token real)
# Por enquanto vou testar sem autenticação para ver se o endpoint responde

url = "http://localhost:8000/produtos/vendaveis"
params = {
    "busca": "test"
}

print("🔍 Testando endpoint:", url)
print("📦 Parâmetros:", params)
print("-" * 50)

try:
    response = requests.get(url, params=params)
    print(f"✅ Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📊 Total de produtos: {data.get('total', 0)}")
        print(f"📄 Produtos na página: {len(data.get('data', []))}")
        
        if data.get('data'):
            print("\n🎯 Primeiros produtos encontrados:")
            for prod in data['data'][:3]:
                print(f"  - {prod['nome']} (Código: {prod['codigo']})")
    else:
        print(f"❌ Erro {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"❌ Erro na requisição: {e}")
