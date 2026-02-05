"""
Teste do endpoint GET /comissoes/funcionarios

Este script testa o novo endpoint que lista funcionários com comissões.

Executar: python test_endpoint_funcionarios.py
"""

import requests
import json

# URL base da API
BASE_URL = "http://localhost:8000"

def test_listar_funcionarios():
    """Testa o endpoint GET /comissoes/funcionarios"""
    
    print("=" * 80)
    print("TESTE: GET /comissoes/funcionarios")
    print("=" * 80)
    
    try:
        # Fazer requisição
        url = f"{BASE_URL}/comissoes/funcionarios"
        print(f"\n📡 Requisição: {url}")
        
        response = requests.get(url)
        
        print(f"\n📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ Resposta bem-sucedida!")
            print(f"\n📋 Estrutura da resposta:")
            print(f"  - success: {data.get('success')}")
            print(f"  - total: {data.get('total')}")
            print(f"  - lista (primeiros 5):")
            
            for func in data.get('lista', [])[:5]:
                print(f"    • ID: {func['id']} - Nome: {func['nome']}")
            
            if data.get('total', 0) > 5:
                print(f"    ... e mais {data.get('total') - 5} funcionários")
            
            print(f"\n📦 Resposta completa:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Validações
            print(f"\n🔍 Validações:")
            assert data['success'] == True, "❌ success deveria ser True"
            print("  ✓ Campo 'success' válido")
            
            assert isinstance(data['lista'], list), "❌ lista deveria ser array"
            print("  ✓ Campo 'lista' é array")
            
            assert data['total'] == len(data['lista']), "❌ total não bate com tamanho da lista"
            print("  ✓ Campo 'total' correto")
            
            if len(data['lista']) > 0:
                primeiro = data['lista'][0]
                assert 'id' in primeiro, "❌ Falta campo 'id'"
                assert 'nome' in primeiro, "❌ Falta campo 'nome'"
                assert isinstance(primeiro['id'], int), "❌ id deveria ser inteiro"
                assert isinstance(primeiro['nome'], str), "❌ nome deveria ser string"
                print("  ✓ Estrutura dos itens válida")
                
                # Verificar ordenação alfabética
                nomes = [f['nome'] for f in data['lista']]
                nomes_ordenados = sorted(nomes)
                if nomes == nomes_ordenados:
                    print("  ✓ Lista ordenada alfabeticamente")
                else:
                    print("  ⚠️  Lista NÃO está ordenada alfabeticamente")
            
            print(f"\n✅ TESTE PASSOU!")
            
        else:
            print(f"\n❌ Erro na requisição:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERRO: Não foi possível conectar ao servidor em {BASE_URL}")
        print("   Certifique-se de que o backend está rodando!")
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_listar_funcionarios()
