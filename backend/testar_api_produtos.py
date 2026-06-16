#!/usr/bin/env python3
"""
Script para testar API de produtos e ver quantos retorna
"""
import requests

def testar_api():
    url = "http://localhost:8000/produtos/"
    headers = {"Authorization": "Bearer admin-dev-token"}
    
    try:
        print("🔍 Testando API de produtos...")
        response = response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Erro: Status {response.status_code}")
            print(f"   Resposta: {response.text[:200]}")
            return
        
        data = response.json()
        
        # Verificar estrutura da resposta
        if isinstance(data, dict):
            produtos = data.get("produtos", [])
            total = data.get("total", None)
            pagina = data.get("pagina", None)
            total_paginas = data.get("total_paginas", None)
            
            print("\n✅ API respondeu com sucesso!")
            print(f"   - Produtos retornados: {len(produtos)}")
            print(f"   - Campo 'total': {total}")
            print(f"   - Campo 'pagina': {pagina}")
            print(f"   - Campo 'total_paginas': {total_paginas}")
            
            if produtos:
                print("\n📦 Exemplo do primeiro produto:")
                primeiro = produtos[0]
                print(f"   - ID: {primeiro.get('id')}")
                print(f"   - Nome: {primeiro.get('nome')}")
                print(f"   - Código: {primeiro.get('codigo')}")
                print(f"   - Tipo: {primeiro.get('tipo_produto')}")
        else:
            produtos = data if isinstance(data, list) else []
            print("\n✅ API retornou lista direta!")
            print(f"   - Produtos: {len(produtos)}")
        
        # Verificar tipos de produto
        if produtos:
            print("\n📊 Distribuição por tipo:")
            tipos = {}
            for p in produtos:
                tipo = p.get('tipo_produto', 'DESCONHECIDO')
                tipos[tipo] = tipos.get(tipo, 0) + 1
            
            for tipo, qtd in sorted(tipos.items()):
                print(f"   - {tipo}: {qtd}")
                
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

if __name__ == "__main__":
    testar_api()
