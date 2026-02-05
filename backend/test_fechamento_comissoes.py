"""
Teste do endpoint de fechamento de comissões
"""
import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("TESTE: FECHAMENTO DE COMISSÕES")
print("=" * 80)

# 1. Fazer login
print("\n1. Fazendo login...")
login_response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "admin@test.com",
    "password": "admin123"
})

if login_response.status_code != 200:
    print(f"❌ Erro no login: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ Login realizado com sucesso")

# 2. Listar comissões pendentes
print("\n2. Listando comissões pendentes...")
comissoes_response = requests.get(f"{BASE_URL}/comissoes?status=pendente", headers=headers)

if comissoes_response.status_code != 200:
    print(f"❌ Erro ao listar comissões: {comissoes_response.status_code}")
    exit(1)

comissoes_data = comissoes_response.json()
comissoes_pendentes = comissoes_data.get('lista', [])

print(f"✅ Encontradas {len(comissoes_pendentes)} comissões pendentes")

if len(comissoes_pendentes) == 0:
    print("⚠️ Não há comissões pendentes para testar o fechamento")
    exit(0)

# Pegar IDs das primeiras 2 comissões
ids_para_fechar = [c['id'] for c in comissoes_pendentes[:2]]
print(f"📋 IDs selecionados para fechamento: {ids_para_fechar}")

# 3. Fechar comissões
print("\n3. Fechando comissões...")
fechamento_payload = {
    "comissoes_ids": ids_para_fechar,
    "data_pagamento": str(date.today()),
    "observacao": "Teste de fechamento via API"
}

print(f"📤 Payload: {json.dumps(fechamento_payload, indent=2)}")

fechamento_response = requests.post(
    f"{BASE_URL}/comissoes/fechar",
    json=fechamento_payload,
    headers=headers
)

print(f"\n📊 Status Code: {fechamento_response.status_code}")
print(f"📥 Response:")
print(json.dumps(fechamento_response.json(), indent=2, ensure_ascii=False))

if fechamento_response.status_code == 200:
    result = fechamento_response.json()
    print(f"\n✅ Fechamento realizado com sucesso!")
    print(f"   - Processadas: {result['total_processadas']}")
    print(f"   - Ignoradas: {result['total_ignoradas']}")
    print(f"   - Valor total: R$ {result['valor_total_fechamento']:.2f}")
else:
    print(f"\n❌ Erro no fechamento")

# 4. Verificar status das comissões fechadas
print("\n4. Verificando status após fechamento...")
for comissao_id in ids_para_fechar:
    detalhe_response = requests.get(f"{BASE_URL}/comissoes/{comissao_id}", headers=headers)
    if detalhe_response.status_code == 200:
        detalhe = detalhe_response.json()['comissao']
        print(f"   - Comissão {comissao_id}: status = {detalhe['status']}, data_pagamento = {detalhe.get('data_pagamento', 'N/A')}")
    else:
        print(f"   ❌ Erro ao buscar comissão {comissao_id}")

print("\n" + "=" * 80)
print("TESTE CONCLUÍDO")
print("=" * 80)
