"""
Script para criar templates via API seed
"""
import requests

# Fazer login para obter token
print("🔐 Fazendo login...")
login_response = requests.post('http://127.0.0.1:8000/auth/login-multitenant', json={
    'username': 'admin',
    'password': 'admin'
})

if login_response.status_code != 200:
    print(f'❌ Erro no login: {login_response.status_code} - {login_response.text}')
    exit(1)

token = login_response.json()['access_token']
print('✅ Login realizado\n')

# Chamar seed de templates
print("🌱 Criando templates...")
seed_response = requests.post(
    'http://127.0.0.1:8000/api/admin/seed/adquirentes',
    headers={'Authorization': f'Bearer {token}'}
)

if seed_response.status_code != 200:
    print(f'❌ Erro ao criar templates: {seed_response.status_code} - {seed_response.text}')
    exit(1)

result = seed_response.json()
print(f"\n✅ Templates criados: {result['total_criados']}")
print(f"📋 Adquirentes: {', '.join(result['adquirentes'])}")

# Verificar template Stone
print("\n🔍 Verificando template Stone...")
templates_response = requests.get(
    'http://127.0.0.1:8000/api/conciliacao/templates',
    headers={'Authorization': f'Bearer {token}'}
)

if templates_response.status_code == 200:
    templates = templates_response.json()
    stone_templates = [t for t in templates if 'stone' in t.get('nome', '').lower()]
    if stone_templates:
        stone = stone_templates[0]
        print(f"✅ Template Stone encontrado (ID: {stone.get('id')})")
        if 'mapeamento' in stone:
            nsu_col = stone['mapeamento'].get('nsu', {}).get('coluna', 'N/A')
            print(f"   Coluna NSU: {nsu_col}")
