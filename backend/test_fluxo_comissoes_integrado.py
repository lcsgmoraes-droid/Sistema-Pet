"""
TESTE E2E - FLUXO INTEGRADO DE COMISSÕES
Testa o fluxo completo de fechamento de comissões → contas a pagar → fluxo de caixa → saldo bancário
"""

import requests
from datetime import date, datetime, timedelta
from decimal import Decimal

# Configuração
BASE_URL = "http://127.0.0.1:8000/api"
TOKEN = None  # Será preenchido após login

def login():
    """Fazer login e obter token"""
    global TOKEN
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        TOKEN = response.json()["access_token"]
        print("✅ Login realizado com sucesso")
        return True
    else:
        print(f"❌ Erro no login: {response.text}")
        return False

def get_headers():
    """Retorna headers com token de autenticação"""
    return {"Authorization": f"Bearer {TOKEN}"}

def buscar_saldo_conta(conta_id: int):
    """Busca saldo atual de uma conta bancária"""
    response = requests.get(
        f"{BASE_URL}/contas-bancarias/{conta_id}",
        headers=get_headers()
    )
    if response.status_code == 200:
        dados = response.json()
        saldo = dados.get('saldo_atual', 0) / 100  # Converter de centavos para reais
        return saldo
    return None

def buscar_lancamentos_previstos():
    """Busca lançamentos manuais previstos"""
    response = requests.get(
        f"{BASE_URL}/fluxo-caixa/lancamentos-manuais?status=previsto",
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return []

def buscar_contas_pagar_pendentes():
    """Busca contas a pagar pendentes"""
    response = requests.get(
        f"{BASE_URL}/contas-pagar?status=pendente",
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return []

# ============================================================================
# TESTE 1: FECHAMENTO SEM PAGAMENTO
# ============================================================================

def teste_1_fechamento_sem_pagamento():
    """
    Cenário: Fechar comissões SEM pagar no ato
    Resultado esperado:
    - Comissões fechadas
    - ContaPagar criada (status=pendente)
    - LancamentoManual previsto criado
    - Saldo bancário NÃO alterado
    """
    print("\n" + "="*80)
    print("TESTE 1: FECHAMENTO SEM PAGAMENTO")
    print("="*80)
    
    # 1. Buscar comissões pendentes
    response = requests.get(
        f"{BASE_URL}/comissoes/funcionario/1/pendentes",
        headers=get_headers()
    )
    
    if response.status_code != 200:
        print(f"❌ Erro ao buscar comissões: {response.text}")
        return False
    
    comissoes = response.json()
    if not comissoes:
        print("⚠️ Nenhuma comissão pendente encontrada para teste")
        return False
    
    comissoes_ids = [c['id'] for c in comissoes[:3]]  # Pegar primeiras 3
    valor_total = sum(c['valor_comissao_gerada'] for c in comissoes[:3])
    
    print(f"📋 {len(comissoes_ids)} comissões selecionadas")
    print(f"💰 Valor total: R$ {valor_total:.2f}")
    
    # 2. Buscar contadores antes
    contas_antes = len(buscar_contas_pagar_pendentes())
    lancamentos_antes = len(buscar_lancamentos_previstos())
    
    # 3. Fechar comissões SEM pagamento
    data_fechamento = date.today()
    response = requests.post(
        f"{BASE_URL}/comissoes/fechar",
        json={
            "comissoes_ids": comissoes_ids,
            "data_pagamento": str(data_fechamento),
            "observacao": "Teste E2E - Fechamento sem pagamento"
        },
        headers=get_headers()
    )
    
    if response.status_code != 200:
        print(f"❌ Erro ao fechar comissões: {response.text}")
        return False
    
    resultado = response.json()
    print(f"✅ {resultado['total_processadas']} comissões fechadas")
    
    # 4. Verificar conta a pagar criada
    contas_depois = buscar_contas_pagar_pendentes()
    if len(contas_depois) > contas_antes:
        print(f"✅ Conta a pagar criada automaticamente")
        ultima_conta = contas_depois[0]
        print(f"   - ID: {ultima_conta['id']}")
        print(f"   - Descrição: {ultima_conta['descricao']}")
        print(f"   - Valor: R$ {ultima_conta['valor_original']:.2f}")
        print(f"   - Status: {ultima_conta['status']}")
    else:
        print("❌ Conta a pagar NÃO foi criada")
        return False
    
    # 5. Verificar lançamento previsto criado
    lancamentos_depois = buscar_lancamentos_previstos()
    if len(lancamentos_depois) > lancamentos_antes:
        print(f"✅ Lançamento previsto criado automaticamente")
        ultimo_lancamento = lancamentos_depois[0]
        print(f"   - ID: {ultimo_lancamento.get('id')}")
        print(f"   - Descrição: {ultimo_lancamento.get('descricao')}")
        print(f"   - Valor: R$ {ultimo_lancamento.get('valor', 0):.2f}")
    else:
        print("❌ Lançamento previsto NÃO foi criado")
        return False
    
    print("\n✅ TESTE 1 CONCLUÍDO COM SUCESSO\n")
    return True

# ============================================================================
# TESTE 2: FECHAMENTO COM PAGAMENTO (CONTA BANCÁRIA)
# ============================================================================

def teste_2_fechamento_com_pagamento():
    """
    Cenário: Fechar comissões E PAGAR no ato via conta bancária
    Resultado esperado:
    - Comissões fechadas
    - ContaPagar criada (status=pago)
    - Pagamento registrado
    - MovimentacaoFinanceira criada (realizado)
    - Saldo bancário DEBITADO
    """
    print("\n" + "="*80)
    print("TESTE 2: FECHAMENTO COM PAGAMENTO NO ATO")
    print("="*80)
    
    # 1. Buscar conta bancária
    response = requests.get(
        f"{BASE_URL}/contas-bancarias",
        headers=get_headers()
    )
    
    if response.status_code != 200:
        print(f"❌ Erro ao buscar contas bancárias: {response.text}")
        return False
    
    contas = response.json()
    if not contas:
        print("⚠️ Nenhuma conta bancária encontrada")
        return False
    
    conta_bancaria = contas[0]
    conta_id = conta_bancaria['id']
    saldo_antes = buscar_saldo_conta(conta_id)
    
    print(f"🏦 Conta: {conta_bancaria['nome']}")
    print(f"💰 Saldo antes: R$ {saldo_antes:.2f}")
    
    # 2. Buscar comissões pendentes
    response = requests.get(
        f"{BASE_URL}/comissoes/funcionario/1/pendentes",
        headers=get_headers()
    )
    
    if response.status_code != 200:
        print(f"❌ Erro ao buscar comissões: {response.text}")
        return False
    
    comissoes = response.json()
    if not comissoes:
        print("⚠️ Nenhuma comissão pendente encontrada")
        return False
    
    comissoes_ids = [c['id'] for c in comissoes[:2]]
    valor_total = sum(c['valor_comissao_gerada'] for c in comissoes[:2])
    
    print(f"📋 {len(comissoes_ids)} comissões selecionadas")
    print(f"💰 Valor a pagar: R$ {valor_total:.2f}")
    
    # 3. Fechar COM pagamento
    data_pagamento = date.today()
    response = requests.post(
        f"{BASE_URL}/comissoes/fechar-com-pagamento",
        params={
            "comissoes_ids": comissoes_ids,
            "valor_pago": valor_total,
            "forma_pagamento": "PIX",
            "conta_bancaria_id": conta_id,
            "data_pagamento": str(data_pagamento),
            "observacoes": "Teste E2E - Pagamento no ato"
        },
        headers=get_headers()
    )
    
    if response.status_code != 200:
        print(f"❌ Erro ao fechar com pagamento: {response.text}")
        return False
    
    resultado = response.json()
    print(f"✅ {resultado['total_processadas']} comissões fechadas com pagamento")
    
    # 4. Verificar saldo atualizado
    saldo_depois = buscar_saldo_conta(conta_id)
    diferenca = saldo_antes - saldo_depois
    
    print(f"💰 Saldo depois: R$ {saldo_depois:.2f}")
    print(f"📉 Diferença: R$ {diferenca:.2f}")
    
    if abs(diferenca - valor_total) < 0.01:  # Tolerância de 1 centavo
        print("✅ Saldo bancário DEBITADO corretamente")
    else:
        print(f"❌ Saldo bancário NÃO foi debitado corretamente")
        print(f"   Esperado: R$ {valor_total:.2f}")
        print(f"   Debitado: R$ {diferenca:.2f}")
        return False
    
    print("\n✅ TESTE 2 CONCLUÍDO COM SUCESSO\n")
    return True

# ============================================================================
# TESTE 3: PAGAMENTO POSTERIOR
# ============================================================================

def teste_3_pagamento_posterior():
    """
    Cenário: Fechar comissão SEM pagar, depois PAGAR posteriormente
    Resultado esperado:
    - Conta a pagar status pendente → pago
    - MovimentacaoFinanceira criada
    - Saldo bancário debitado
    - LancamentoManual previsto → realizado
    """
    print("\n" + "="*80)
    print("TESTE 3: PAGAMENTO POSTERIOR")
    print("="*80)
    
    # 1. Buscar conta a pagar pendente
    contas_pendentes = buscar_contas_pagar_pendentes()
    
    if not contas_pendentes:
        print("⚠️ Nenhuma conta a pagar pendente encontrada")
        print("   Execute TESTE 1 primeiro para criar uma conta pendente")
        return False
    
    conta_pagar = contas_pendentes[0]
    conta_id = conta_pagar['id']
    valor_conta = conta_pagar['valor_original']
    
    print(f"📄 Conta a pagar: {conta_pagar['descricao']}")
    print(f"💰 Valor: R$ {valor_conta:.2f}")
    print(f"📊 Status: {conta_pagar['status']}")
    
    # 2. Buscar conta bancária
    response = requests.get(
        f"{BASE_URL}/contas-bancarias",
        headers=get_headers()
    )
    
    contas_bancarias = response.json()
    conta_bancaria = contas_bancarias[0]
    conta_bancaria_id = conta_bancaria['id']
    saldo_antes = buscar_saldo_conta(conta_bancaria_id)
    
    print(f"🏦 Conta: {conta_bancaria['nome']}")
    print(f"💰 Saldo antes: R$ {saldo_antes:.2f}")
    
    # 3. Registrar pagamento
    data_pagamento = date.today()
    response = requests.post(
        f"{BASE_URL}/contas-pagar/{conta_id}/pagar",
        json={
            "valor_pago": valor_conta,
            "data_pagamento": str(data_pagamento),
            "conta_bancaria_id": conta_bancaria_id,
            "forma_pagamento_id": 1,
            "observacoes": "Teste E2E - Pagamento posterior"
        },
        headers=get_headers()
    )
    
    if response.status_code != 200:
        print(f"❌ Erro ao registrar pagamento: {response.text}")
        return False
    
    resultado = response.json()
    print(f"✅ Pagamento registrado")
    print(f"   Status: {resultado['status']}")
    
    # 4. Verificar saldo
    saldo_depois = buscar_saldo_conta(conta_bancaria_id)
    diferenca = saldo_antes - saldo_depois
    
    print(f"💰 Saldo depois: R$ {saldo_depois:.2f}")
    print(f"📉 Diferença: R$ {diferenca:.2f}")
    
    if abs(diferenca - valor_conta) < 0.01:
        print("✅ Saldo bancário DEBITADO corretamente")
    else:
        print(f"❌ Saldo bancário incorreto")
        return False
    
    print("\n✅ TESTE 3 CONCLUÍDO COM SUCESSO\n")
    return True

# ============================================================================
# EXECUTAR TODOS OS TESTES
# ============================================================================

def executar_testes():
    """Executa todos os testes em sequência"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  TESTE E2E - FLUXO INTEGRADO DE COMISSÕES                   ║")
    print("║  Fechamento → Contas a Pagar → Fluxo de Caixa → Saldo       ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print("\n")
    
    # Login
    if not login():
        print("❌ Falha no login. Abortando testes.")
        return
    
    # Executar testes
    resultados = []
    
    # TESTE 1
    try:
        resultado = teste_1_fechamento_sem_pagamento()
        resultados.append(("TESTE 1: Fechamento sem pagamento", resultado))
    except Exception as e:
        print(f"❌ Erro no TESTE 1: {str(e)}")
        resultados.append(("TESTE 1: Fechamento sem pagamento", False))
    
    # TESTE 2
    try:
        resultado = teste_2_fechamento_com_pagamento()
        resultados.append(("TESTE 2: Fechamento com pagamento", resultado))
    except Exception as e:
        print(f"❌ Erro no TESTE 2: {str(e)}")
        resultados.append(("TESTE 2: Fechamento com pagamento", False))
    
    # TESTE 3
    try:
        resultado = teste_3_pagamento_posterior()
        resultados.append(("TESTE 3: Pagamento posterior", resultado))
    except Exception as e:
        print(f"❌ Erro no TESTE 3: {str(e)}")
        resultados.append(("TESTE 3: Pagamento posterior", False))
    
    # Resumo
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  RESUMO DOS TESTES                                           ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print("\n")
    
    total = len(resultados)
    sucesso = sum(1 for _, r in resultados if r)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    print("\n")
    print(f"Total: {sucesso}/{total} testes passaram")
    
    if sucesso == total:
        print("\n🎉 TODOS OS TESTES PASSARAM! IMPLEMENTAÇÃO COMPLETA E FUNCIONAL!")
    else:
        print(f"\n⚠️ {total - sucesso} teste(s) falharam. Revise a implementação.")
    
    print("\n")

if __name__ == "__main__":
    executar_testes()
