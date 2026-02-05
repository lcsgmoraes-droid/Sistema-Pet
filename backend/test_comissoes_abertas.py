"""
TESTE DO ENDPOINT: GET /comissoes/abertas
Sprint 6 - Passo 1/5

Valida:
- Endpoint responde corretamente
- Estrutura da resposta está correta
- Dados estão formatados adequadamente
"""

import requests
import json

# Configuração
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"
COMISSOES_URL = f"{BASE_URL}/comissoes/abertas"

# Credenciais (ajustar conforme necessário)
USERNAME = "admin@test.com"
PASSWORD = "admin123"

def main():
    print("=" * 60)
    print("TESTE: GET /comissoes/abertas")
    print("=" * 60)
    
    # 1. Login
    print("\n[1/2] Fazendo login...")
    try:
        login_response = requests.post(
            LOGIN_URL,
            json={
                "email": USERNAME,
                "password": PASSWORD
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Erro no login: {login_response.status_code}")
            print(login_response.text)
            return
        
        token = login_response.json()["access_token"]
        print(f"✅ Login bem-sucedido!")
        
    except Exception as e:
        print(f"❌ Erro ao fazer login: {str(e)}")
        return
    
    # 2. Consultar comissões abertas
    print("\n[2/2] Consultando comissões em aberto...")
    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(COMISSOES_URL, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Erro na requisição: {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        
        # Validar estrutura
        assert "success" in data, "Campo 'success' ausente"
        assert "total_funcionarios" in data, "Campo 'total_funcionarios' ausente"
        assert "funcionarios" in data, "Campo 'funcionarios' ausente"
        
        print(f"✅ Requisição bem-sucedida!")
        print(f"\n{'=' * 60}")
        print("RESULTADO:")
        print(f"{'=' * 60}")
        print(f"Total de funcionários: {data['total_funcionarios']}")
        print(f"\nFuncionários com comissões pendentes:\n")
        
        if data['total_funcionarios'] == 0:
            print("   Nenhum funcionário com comissões pendentes")
        else:
            total_geral = 0
            total_comissoes = 0
            
            for i, func in enumerate(data['funcionarios'], 1):
                print(f"{i}. {func['nome_funcionario']} (ID: {func['funcionario_id']})")
                print(f"   Total Pendente: R$ {func['total_pendente']:.2f}")
                print(f"   Quantidade: {func['quantidade_comissoes']} comissão(ões)")
                print(f"   Última Venda: {func['data_ultima_venda']}")
                print()
                
                total_geral += func['total_pendente']
                total_comissoes += func['quantidade_comissoes']
            
            print(f"{'=' * 60}")
            print(f"TOTAIS GERAIS:")
            print(f"  - Valor total pendente: R$ {total_geral:.2f}")
            print(f"  - Total de comissões: {total_comissoes}")
            print(f"{'=' * 60}")
        
        # Exibir JSON completo
        print(f"\n{'=' * 60}")
        print("JSON COMPLETO:")
        print(f"{'=' * 60}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
    except AssertionError as e:
        print(f"❌ Erro de validação: {str(e)}")
    except Exception as e:
        print(f"❌ Erro ao consultar comissões: {str(e)}")

if __name__ == "__main__":
    main()
