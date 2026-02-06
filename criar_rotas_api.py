"""
Script para criar rotas retroativas via API do backend
"""
import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

# Headers com tenant
headers = {
    "X-Tenant-ID": "7be8dad7-8956-4758-b7bc-855a5259fe2b",
    "Content-Type": "application/json"
}

# 1. Buscar vendas sem rota
print("Buscando vendas abertas com entrega...")
response = requests.get(f"{BASE_URL}/vendas/", params={"status": "aberta"}, headers=headers)

if response.status_code != 200:
    print(f"❌ Erro ao buscar vendas: {response.status_code}")
    print(response.text)
    exit(1)

vendas = response.json().get("items", [])
print(f"✓ Encontradas {len(vendas)} vendas abertas")

# Filtrar vendas com entrega
vendas_com_entrega = [v for v in vendas if v.get("tem_entrega") == True]
print(f"✓ {len(vendas_com_entrega)} vendas com entrega")

# 2. Buscar rotas existentes
print("\nBuscando rotas existentes...")
response = requests.get(f"{BASE_URL}/rotas-entrega/", headers=headers)

if response.status_code != 200:
    print(f"❌ Erro ao buscar rotas: {response.status_code}")
    exit(1)

rotas = response.json()
venda_ids_com_rota = {r["venda_id"] for r in rotas}
print(f"✓ {len(rotas)} rotas existentes")

# 3. Filtrar vendas sem rota
vendas_sem_rota = [v for v in vendas_com_entrega if v["id"] not in venda_ids_com_rota]
print(f"✓ {len(vendas_sem_rota)} vendas SEM rota\n")

# 4. Buscar entregador padrão
print("Buscando entregador padrão...")
response = requests.get(f"{BASE_URL}/clientes/", headers=headers)

if response.status_code != 200:
    print(f"❌ Erro ao buscar clientes: {response.status_code}")
    exit(1)

clientes = response.json().get("items", [])
entregador_padrao = next(
    (c for c in clientes if c.get("entregador_padrao") and c.get("entregador_ativo")),
    None
)

if not entregador_padrao:
    print("❌ Nenhum entregador padrão encontrado!")
    exit(1)

print(f"✓ Entregador: {entregador_padrao['nome']} (ID: {entregador_padrao['id']})\n")

# 5. Criar rotas
rotas_criadas = 0

for venda in vendas_sem_rota:
    print(f"Criando rota para venda {venda['numero_venda']}...")
    print(f"  Endereço: {venda.get('endereco_entrega', 'N/A')[:80]}...")
    
    rota_data = {
        "venda_id": venda["id"],
        "entregador_id": entregador_padrao["id"],
        "endereco_destino": venda.get("endereco_entrega", ""),
        "status": "pendente",
        "taxa_entrega_cliente": venda.get("taxa_entrega", 0.0)
    }
    
    response = requests.post(
        f"{BASE_URL}/rotas-entrega/",
        headers=headers,
        json=rota_data
    )
    
    if response.status_code in [200, 201]:
        rotas_criadas += 1
        print(f"  ✅ Rota criada!\n")
    else:
        print(f"  ❌ Erro: {response.status_code} - {response.text}\n")

print(f"{'='*60}")
print(f"✅ SUCESSO: {rotas_criadas} de {len(vendas_sem_rota)} rotas criadas!")
print(f"{'='*60}")
