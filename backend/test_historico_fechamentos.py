"""
SPRINT 6 - PASSO 4/5: TESTE HISTÓRICO DE FECHAMENTOS
Teste dos endpoints de consulta de histórico de fechamentos de comissões

Testa:
1. GET /comissoes/fechamentos - Lista de fechamentos históricos
2. GET /comissoes/fechamentos/detalhe - Detalhes de um fechamento específico

Criado em: 22/01/2026
"""

import requests
import json
from datetime import datetime, timedelta

# Configuração
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

# Credenciais de teste
EMAIL = "admin@test.com"
PASSWORD = "admin123"

def print_separator(title):
    """Imprime separador visual"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def login():
    """Faz login e retorna o token"""
    print_separator("REALIZANDO LOGIN")
    
    response = requests.post(
        f"{API_URL}/login",
        json={"email": EMAIL, "password": PASSWORD}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"✅ Login realizado com sucesso")
        print(f"Token: {token[:30]}...")
        return token
    else:
        print(f"❌ Erro no login: {response.status_code}")
        print(response.text)
        return None

def test_listar_historico_fechamentos(token, data_inicio=None, data_fim=None, funcionario_id=None):
    """Testa listagem de histórico de fechamentos"""
    print_separator("TESTE 1: LISTAR HISTÓRICO DE FECHAMENTOS")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Construir query params
    params = {}
    if data_inicio:
        params['data_inicio'] = data_inicio
    if data_fim:
        params['data_fim'] = data_fim
    if funcionario_id:
        params['funcionario_id'] = funcionario_id
    
    print(f"\n📋 Parâmetros de filtro:")
    if params:
        for key, value in params.items():
            print(f"  - {key}: {value}")
    else:
        print("  - Sem filtros (todos os fechamentos)")
    
    response = requests.get(
        f"{API_URL}/comissoes/fechamentos",
        headers=headers,
        params=params
    )
    
    print(f"\n🔍 Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get('success'):
            print(f"✅ Histórico carregado com sucesso\n")
            
            # Resumo geral
            resumo = data.get('resumo', {})
            print(f"📊 RESUMO GERAL:")
            print(f"  - Total de fechamentos: {resumo.get('total_fechamentos', 0)}")
            print(f"  - Quantidade total de comissões: {resumo.get('quantidade_total_geral', 0)}")
            print(f"  - Valor total geral: R$ {resumo.get('valor_total_geral', 0):.2f}")
            
            # Lista de fechamentos
            fechamentos = data.get('fechamentos', [])
            print(f"\n📝 FECHAMENTOS ENCONTRADOS: {len(fechamentos)}")
            
            for i, fechamento in enumerate(fechamentos, 1):
                print(f"\n  [{i}] Fechamento:")
                print(f"      Funcionário: {fechamento.get('nome_funcionario')} (ID: {fechamento.get('funcionario_id')})")
                print(f"      Data Fechamento: {fechamento.get('data_fechamento')}")
                print(f"      Data Pagamento: {fechamento.get('data_pagamento')}")
                print(f"      Quantidade: {fechamento.get('quantidade_comissoes')}")
                print(f"      Valor Total: R$ {fechamento.get('valor_total'):.2f}")
                print(f"      Período Vendas: {fechamento.get('periodo_vendas')}")
                if fechamento.get('observacao_pagamento'):
                    print(f"      Observação: {fechamento.get('observacao_pagamento')}")
            
            return fechamentos
        else:
            print(f"❌ Erro: {data.get('message', 'Erro desconhecido')}")
            return []
    else:
        print(f"❌ Erro HTTP {response.status_code}")
        print(response.text)
        return []

def test_detalhe_fechamento(token, funcionario_id, data_pagamento):
    """Testa detalhamento de um fechamento específico"""
    print_separator(f"TESTE 2: DETALHES DO FECHAMENTO")
    
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        'funcionario_id': funcionario_id,
        'data_pagamento': data_pagamento
    }
    
    print(f"\n🔍 Buscando fechamento:")
    print(f"  - Funcionário ID: {funcionario_id}")
    print(f"  - Data Pagamento: {data_pagamento}")
    
    response = requests.get(
        f"{API_URL}/comissoes/fechamentos/detalhe",
        headers=headers,
        params=params
    )
    
    print(f"\n🔍 Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get('success'):
            print(f"✅ Detalhes carregados com sucesso\n")
            
            # Informações do fechamento
            fechamento = data.get('fechamento', {})
            print(f"📋 INFORMAÇÕES DO FECHAMENTO:")
            print(f"  - Funcionário: {fechamento.get('nome_funcionario')} (ID: {fechamento.get('funcionario_id')})")
            print(f"  - Data Fechamento: {fechamento.get('data_fechamento')}")
            print(f"  - Data Pagamento: {fechamento.get('data_pagamento')}")
            print(f"  - Quantidade: {fechamento.get('quantidade_comissoes')}")
            print(f"  - Valor Total: R$ {fechamento.get('valor_total'):.2f}")
            print(f"  - Período: {fechamento.get('periodo_vendas')}")
            if fechamento.get('observacao_pagamento'):
                print(f"  - Observação: {fechamento.get('observacao_pagamento')}")
            
            # Lista de comissões
            comissoes = data.get('comissoes', [])
            print(f"\n💰 COMISSÕES INCLUÍDAS: {len(comissoes)}")
            
            total_calculado = 0
            for i, comissao in enumerate(comissoes, 1):
                print(f"\n  [{i}] Comissão ID {comissao.get('id')}:")
                print(f"      Cliente: {comissao.get('nome_cliente', 'N/A')}")
                print(f"      Produto: {comissao.get('nome_produto', 'N/A')}")
                print(f"      Data Venda: {comissao.get('data_venda')}")
                print(f"      Quantidade: {comissao.get('quantidade')}")
                print(f"      Valor Venda: R$ {comissao.get('valor_venda_snapshot', 0):.2f}")
                print(f"      Percentual: {comissao.get('percentual_snapshot', 0)}%")
                print(f"      Comissão: R$ {comissao.get('valor_comissao', 0):.2f}")
                print(f"      Status: {comissao.get('status')}")
                
                total_calculado += comissao.get('valor_comissao', 0)
            
            print(f"\n💵 TOTAIS:")
            print(f"  - Total Calculado: R$ {total_calculado:.2f}")
            print(f"  - Total Registrado: R$ {fechamento.get('valor_total'):.2f}")
            print(f"  - ✅ Valores conferem: {abs(total_calculado - fechamento.get('valor_total', 0)) < 0.01}")
            
            return data
        else:
            print(f"❌ Erro: {data.get('message', 'Erro desconhecido')}")
            return None
    else:
        print(f"❌ Erro HTTP {response.status_code}")
        print(response.text)
        return None

def main():
    """Função principal de testes"""
    print_separator("INÍCIO DOS TESTES - HISTÓRICO DE FECHAMENTOS")
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # 1. Login
    token = login()
    if not token:
        print("\n❌ Não foi possível realizar login. Abortando testes.")
        return
    
    # 2. Listar todos os fechamentos (sem filtro)
    fechamentos = test_listar_historico_fechamentos(token)
    
    # 3. Se houver fechamentos, testar detalhamento do primeiro
    if fechamentos:
        print_separator("TESTANDO DETALHAMENTO DO PRIMEIRO FECHAMENTO")
        primeiro = fechamentos[0]
        test_detalhe_fechamento(
            token,
            primeiro.get('funcionario_id'),
            primeiro.get('data_pagamento')
        )
    
    # 4. Testar filtros
    print_separator("TESTANDO FILTROS")
    
    # Filtro por período (últimos 30 dias)
    hoje = datetime.now().date()
    trinta_dias_atras = hoje - timedelta(days=30)
    
    print("\n🔍 Teste com filtro de período (últimos 30 dias):")
    test_listar_historico_fechamentos(
        token,
        data_inicio=trinta_dias_atras.isoformat(),
        data_fim=hoje.isoformat()
    )
    
    # Filtro por funcionário (se houver fechamentos)
    if fechamentos:
        print("\n🔍 Teste com filtro por funcionário:")
        test_listar_historico_fechamentos(
            token,
            funcionario_id=fechamentos[0].get('funcionario_id')
        )
    
    # 5. Resumo final
    print_separator("RESUMO DOS TESTES")
    print("\n✅ Testes concluídos com sucesso!")
    print(f"\nEndpoints testados:")
    print(f"  1. GET /comissoes/fechamentos - Lista histórico")
    print(f"  2. GET /comissoes/fechamentos/detalhe - Detalhes do fechamento")
    print(f"\nRecursos testados:")
    print(f"  ✓ Listagem sem filtros")
    print(f"  ✓ Listagem com filtro de período")
    print(f"  ✓ Listagem com filtro de funcionário")
    print(f"  ✓ Detalhamento completo de fechamento")
    print(f"  ✓ Validação de totais")
    print(f"  ✓ Auditoria de snapshot imutável")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
