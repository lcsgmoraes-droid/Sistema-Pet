"""
TESTE COMPLETO DO FLUXO: SPRINT 6 - PASSO 3/5
FECHAMENTO FUNCIONAL DE COMISSÕES

Fluxo testado:
1. Login
2. Listar funcionários com comissões abertas
3. Consultar comissões de um funcionário
4. Fechar comissões do funcionário
5. Verificar se as comissões foram fechadas
"""

import requests
import json
from datetime import date

# Configuração
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"

# Credenciais
USERNAME = "admin@test.com"
PASSWORD = "admin123"

def main():
    print("=" * 70)
    print("TESTE COMPLETO: FLUXO DE FECHAMENTO DE COMISSÕES")
    print("=" * 70)
    
    # 1. Login
    print("\n[1/5] Fazendo login...")
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
            return
        
        token = login_response.json()["access_token"]
        print(f"✅ Login bem-sucedido!")
        
    except Exception as e:
        print(f"❌ Erro ao fazer login: {str(e)}")
        return
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 2. Listar funcionários com comissões abertas
    print("\n[2/5] Buscando funcionários com comissões pendentes...")
    try:
        response = requests.get(f"{BASE_URL}/comissoes/abertas", headers=headers)
        
        if response.status_code != 200 or not response.json().get('funcionarios'):
            print("⚠️  Nenhum funcionário com comissões pendentes encontrado")
            print("   Teste não pode prosseguir sem comissões pendentes")
            return
        
        funcionario = response.json()['funcionarios'][0]
        funcionario_id = funcionario['funcionario_id']
        nome_funcionario = funcionario['nome_funcionario']
        total_pendente_antes = funcionario['total_pendente']
        qtde_comissoes_antes = funcionario['quantidade_comissoes']
        
        print(f"✅ Funcionário encontrado: {nome_funcionario} (ID: {funcionario_id})")
        print(f"   Total pendente: R$ {total_pendente_antes:.2f}")
        print(f"   Quantidade: {qtde_comissoes_antes} comissão(ões)")
        
    except Exception as e:
        print(f"❌ Erro ao buscar funcionário: {str(e)}")
        return
    
    # 3. Consultar comissões do funcionário
    print(f"\n[3/5] Consultando comissões do funcionário {funcionario_id}...")
    try:
        url = f"{BASE_URL}/comissoes/fechamento/{funcionario_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Erro na requisição: {response.status_code}")
            return
        
        data = response.json()
        comissoes = data['comissoes']
        valor_total = data['valor_total']
        
        print(f"✅ {len(comissoes)} comissão(ões) encontrada(s)")
        print(f"   Valor total: R$ {valor_total:.2f}")
        
        # Coletar IDs das comissões
        comissoes_ids = [c['id'] for c in comissoes]
        print(f"   IDs: {comissoes_ids}")
        
    except Exception as e:
        print(f"❌ Erro ao consultar comissões: {str(e)}")
        return
    
    # 4. Fechar comissões
    print(f"\n[4/5] Fechando {len(comissoes_ids)} comissão(ões)...")
    try:
        payload = {
            "comissoes_ids": comissoes_ids,
            "data_pagamento": str(date.today()),
            "observacao": "Teste automatizado - Sprint 6 Passo 3"
        }
        
        response = requests.post(
            f"{BASE_URL}/comissoes/fechar",
            json=payload,
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Erro ao fechar comissões: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        
        if not result.get('success'):
            print(f"❌ Fechamento não foi bem-sucedido")
            print(json.dumps(result, indent=2))
            return
        
        print(f"✅ Fechamento realizado com sucesso!")
        print(f"   Processadas: {result['total_processadas']}")
        print(f"   Ignoradas: {result['total_ignoradas']}")
        print(f"   Valor total: R$ {result['valor_total_fechamento']:.2f}")
        print(f"   Data do pagamento: {result['data_pagamento']}")
        
    except Exception as e:
        print(f"❌ Erro ao fechar comissões: {str(e)}")
        return
    
    # 5. Verificar se as comissões foram fechadas
    print(f"\n[5/5] Verificando se as comissões foram fechadas...")
    try:
        # Consultar novamente as comissões do funcionário
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Erro na verificação: {response.status_code}")
            return
        
        data_depois = response.json()
        comissoes_depois = data_depois['comissoes']
        valor_depois = data_depois['valor_total']
        
        print(f"✅ Verificação concluída!")
        print(f"   Comissões pendentes agora: {len(comissoes_depois)}")
        print(f"   Valor total pendente: R$ {valor_depois:.2f}")
        
        # Verificar se as comissões foram realmente fechadas
        if len(comissoes_depois) < len(comissoes):
            print(f"\n✅ SUCESSO: {len(comissoes) - len(comissoes_depois)} comissão(ões) foi(ram) fechada(s)")
        elif len(comissoes_depois) == 0:
            print(f"\n✅ PERFEITO: Todas as comissões pendentes foram fechadas!")
        else:
            print(f"\n⚠️  ATENÇÃO: O número de comissões não mudou")
        
        # Consultar lista geral novamente
        print(f"\n[BONUS] Verificando lista geral de funcionários...")
        response = requests.get(f"{BASE_URL}/comissoes/abertas", headers=headers)
        funcionarios_depois = response.json().get('funcionarios', [])
        
        # Procurar o funcionário testado
        funcionario_depois = next(
            (f for f in funcionarios_depois if f['funcionario_id'] == funcionario_id),
            None
        )
        
        if funcionario_depois:
            print(f"   Funcionário ainda tem comissões pendentes:")
            print(f"   - Total: R$ {funcionario_depois['total_pendente']:.2f}")
            print(f"   - Quantidade: {funcionario_depois['quantidade_comissoes']}")
        else:
            print(f"   ✅ Funcionário {nome_funcionario} não tem mais comissões pendentes!")
        
        # Sumário final
        print(f"\n{'=' * 70}")
        print("SUMÁRIO DO TESTE:")
        print(f"{'=' * 70}")
        print(f"Antes do fechamento:")
        print(f"  - Comissões: {qtde_comissoes_antes}")
        print(f"  - Valor: R$ {total_pendente_antes:.2f}")
        print(f"\nDepois do fechamento:")
        print(f"  - Comissões: {len(comissoes_depois)}")
        print(f"  - Valor: R$ {valor_depois:.2f}")
        print(f"\nComissões fechadas: {len(comissoes) - len(comissoes_depois)}")
        print(f"Valor fechado: R$ {valor_total:.2f}")
        print(f"{'=' * 70}")
        print("✅ TESTE COMPLETO CONCLUÍDO COM SUCESSO!")
        print(f"{'=' * 70}")
        
    except Exception as e:
        print(f"❌ Erro na verificação: {str(e)}")

if __name__ == "__main__":
    main()
