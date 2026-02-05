"""
TESTE DO ENDPOINT: GET /comissoes/fechamento/{funcionario_id}
Sprint 6 - Passo 2/5

Valida:
- Endpoint responde corretamente
- Filtros de data funcionam
- Estrutura da resposta está correta
- Dados detalhados estão presentes
"""

import requests
import json
from datetime import date, timedelta

# Configuração
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"

# Credenciais
USERNAME = "admin@test.com"
PASSWORD = "admin123"

def main():
    print("=" * 60)
    print("TESTE: GET /comissoes/fechamento/{funcionario_id}")
    print("=" * 60)
    
    # 1. Login
    print("\n[1/4] Fazendo login...")
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
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 2. Buscar funcionário com comissões pendentes
    print("\n[2/4] Buscando funcionário com comissões pendentes...")
    try:
        response = requests.get(f"{BASE_URL}/comissoes/abertas", headers=headers)
        
        if response.status_code != 200 or not response.json().get('funcionarios'):
            print("❌ Nenhum funcionário com comissões pendentes encontrado")
            return
        
        funcionario = response.json()['funcionarios'][0]
        funcionario_id = funcionario['funcionario_id']
        nome_funcionario = funcionario['nome_funcionario']
        
        print(f"✅ Funcionário encontrado: {nome_funcionario} (ID: {funcionario_id})")
        print(f"   Total pendente: R$ {funcionario['total_pendente']:.2f}")
        print(f"   Quantidade: {funcionario['quantidade_comissoes']} comissão(ões)")
        
    except Exception as e:
        print(f"❌ Erro ao buscar funcionário: {str(e)}")
        return
    
    # 3. Consultar comissões do funcionário (sem filtro)
    print(f"\n[3/4] Consultando comissões do funcionário {funcionario_id}...")
    try:
        url = f"{BASE_URL}/comissoes/fechamento/{funcionario_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Erro na requisição: {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        
        # Validar estrutura
        assert "success" in data, "Campo 'success' ausente"
        assert "funcionario" in data, "Campo 'funcionario' ausente"
        assert "total_comissoes" in data, "Campo 'total_comissoes' ausente"
        assert "valor_total" in data, "Campo 'valor_total' ausente"
        assert "comissoes" in data, "Campo 'comissoes' ausente"
        
        print(f"✅ Requisição bem-sucedida!")
        print(f"\n{'=' * 60}")
        print("RESULTADO (SEM FILTRO):")
        print(f"{'=' * 60}")
        print(f"Funcionário: {data['funcionario']['nome']} (ID: {data['funcionario']['id']})")
        print(f"Total de comissões: {data['total_comissoes']}")
        print(f"Valor total: R$ {data['valor_total']:.2f}")
        
        if data['total_comissoes'] > 0:
            print(f"\nPrimeiras comissões:")
            for i, comissao in enumerate(data['comissoes'][:3], 1):
                print(f"\n{i}. Venda #{comissao['venda_id']} - {comissao['data_venda']}")
                print(f"   Produto: {comissao['nome_produto']}")
                print(f"   Cliente: {comissao['cliente_nome']}")
                print(f"   Base: R$ {comissao['valor_base_calculo']:.2f} x {comissao['percentual_comissao']}%")
                print(f"   Comissão: R$ {comissao['valor_comissao_gerada']:.2f}")
            
            if data['total_comissoes'] > 3:
                print(f"\n... e mais {data['total_comissoes'] - 3} comissão(ões)")
        
    except AssertionError as e:
        print(f"❌ Erro de validação: {str(e)}")
        return
    except Exception as e:
        print(f"❌ Erro ao consultar comissões: {str(e)}")
        return
    
    # 4. Testar com filtro de data
    print(f"\n[4/4] Testando filtros de data...")
    try:
        # Filtrar últimos 7 dias
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=7)
        
        params = {
            'data_inicio': str(data_inicio),
            'data_fim': str(data_fim)
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"❌ Erro ao aplicar filtro: {response.status_code}")
            return
        
        data_filtrada = response.json()
        
        print(f"✅ Filtro aplicado com sucesso!")
        print(f"\n{'=' * 60}")
        print(f"RESULTADO (COM FILTRO: {data_inicio} a {data_fim}):")
        print(f"{'=' * 60}")
        print(f"Total de comissões no período: {data_filtrada['total_comissoes']}")
        print(f"Valor total: R$ {data_filtrada['valor_total']:.2f}")
        
        # Exibir JSON completo da primeira consulta
        print(f"\n{'=' * 60}")
        print("JSON COMPLETO (Primeira consulta):")
        print(f"{'=' * 60}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        print(f"\n{'=' * 60}")
        print("✅ TODOS OS TESTES PASSARAM!")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"❌ Erro ao testar filtros: {str(e)}")

if __name__ == "__main__":
    main()
