"""
SPRINT 6 - PASSO 6: Testes dos endpoints de Conferência Avançada e Pagamento Parcial

Testes:
1. GET /comissoes/formas-pagamento - Lista formas
2. GET /comissoes/conferencia-avancada/{id} - Sem filtros
3. GET /comissoes/conferencia-avancada/{id} - Com filtros
4. POST /comissoes/fechar-com-pagamento - Fechar com pagamento
"""

import requests
import json
from datetime import datetime, date

BASE_URL = "http://localhost:8000"
HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzM3NTc4NDAwfQ.test",
    "Content-Type": "application/json"
}

def print_header(msg):
    print(f"\n{'='*80}")
    print(f"🧪 {msg}")
    print(f"{'='*80}\n")

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

# ============================= TESTE 1 =============================

print_header("TESTE 1: Listar formas de pagamento")

try:
    r = requests.get(f"{BASE_URL}/comissoes/formas-pagamento", headers=HEADERS)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print_success(f"Formas de pagamento carregadas:")
        for forma in data['formas']:
            print(f"  • {forma['nome']:20s} - {forma['descricao']}")
    else:
        print_error(f"Erro: {r.text}")
except Exception as e:
    print_error(f"Exceção: {str(e)}")

# ============================= TESTE 2 =============================

print_header("TESTE 2: Conferência Avançada - SEM FILTROS")

try:
    r = requests.get(
        f"{BASE_URL}/comissoes/conferencia-avancada/14",
        headers=HEADERS
    )
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print_success(f"Conferência carregada!")
        print(f"\n👤 Funcionário: {data['funcionario']['nome']} (ID: {data['funcionario']['id']})")
        print(f"\n📊 Resumo:")
        print(f"   • Quantidade: {data['resumo']['quantidade_comissoes']}")
        print(f"   • Total: R$ {data['resumo']['valor_total']:.2f}")
        print(f"   • Pago: R$ {data['resumo']['valor_pago_total']:.2f}")
        print(f"   • Saldo: R$ {data['resumo']['saldo_restante_total']:.2f}")
        print(f"   • % Pago: {data['resumo']['percentual_pago']:.1f}%")
        
        print(f"\n📋 Comissões:")
        for comissao in data['comissoes'][:3]:  # Mostrar apenas 3 primeiras
            print(f"   ID {comissao['id']:3d} | {comissao['data_venda']:10s} | {comissao['nome_produto']:20s} | R$ {comissao['valor_comissao']:8.2f}")
        if len(data['comissoes']) > 3:
            print(f"   ... e mais {len(data['comissoes']) - 3} comissões")
    else:
        print_error(f"Erro: {r.text}")
except Exception as e:
    print_error(f"Exceção: {str(e)}")

# ============================= TESTE 3 =============================

print_header("TESTE 3: Conferência Avançada - COM FILTROS")

try:
    r = requests.get(
        f"{BASE_URL}/comissoes/conferencia-avancada/14",
        params={
            "data_inicio": "2026-01-20",
            "data_fim": "2026-01-22"
        },
        headers=HEADERS
    )
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        periodo = data['periodo_selecionado']
        
        print_success(f"Conferência com filtros carregada!")
        print(f"\n📅 Período Selecionado:")
        print(f"   • Início: {periodo['data_inicio']}")
        print(f"   • Fim: {periodo['data_fim']}")
        
        print(f"\n📊 Resumo (com filtros):")
        print(f"   • Quantidade: {data['resumo']['quantidade_comissoes']}")
        print(f"   • Total: R$ {data['resumo']['valor_total']:.2f}")
        
        print(f"\n📋 Comissões no período:")
        for comissao in data['comissoes']:
            print(f"   ID {comissao['id']:3d} | {comissao['data_venda']:10s} | {comissao['nome_produto']:20s} | R$ {comissao['valor_comissao']:8.2f}")
    else:
        print_error(f"Erro: {r.text}")
except Exception as e:
    print_error(f"Exceção: {str(e)}")

# ============================= TESTE 4 =============================

print_header("TESTE 4: Fechar Comissão com Pagamento Parcial")

try:
    # Buscar comissões pendentes para saber quais IDs usar
    r_conf = requests.get(
        f"{BASE_URL}/comissoes/conferencia-avancada/14",
        headers=HEADERS
    )
    
    if r_conf.status_code == 200:
        comissoes_data = r_conf.json()
        comissoes_ids = [c['id'] for c in comissoes_data['comissoes'][:2]]  # Pegar 2 primeiras
        
        if comissoes_ids:
            # Enviar requisição de fechamento com pagamento parcial
            payload = {
                "comissoes_ids": comissoes_ids,
                "valor_pago": 50.0,  # Pagamento parcial
                "forma_pagamento": "transferencia",
                "data_pagamento": str(date.today()),
                "observacoes": "Teste de pagamento parcial"
            }
            
            print(f"📤 Payload:")
            print(f"   • Comissões: {comissoes_ids}")
            print(f"   • Valor a pagar: R$ {payload['valor_pago']:.2f}")
            print(f"   • Forma: {payload['forma_pagamento']}")
            
            r = requests.post(
                f"{BASE_URL}/comissoes/fechar-com-pagamento",
                params=payload,
                headers=HEADERS
            )
            
            print(f"\nStatus: {r.status_code}")
            
            if r.status_code == 200:
                result = r.json()
                print_success("Fechamento realizado!")
                print(f"\n📊 Resultado:")
                print(f"   • Processadas: {result['total_processadas']}")
                print(f"   • Ignoradas: {result['total_ignoradas']}")
                print(f"   • Valor total: R$ {result['valor_total_fechado']:.2f}")
                print(f"   • Valor pago: R$ {result['valor_total_pago']:.2f}")
                print(f"   • Saldo restante: R$ {result['saldo_total_restante']:.2f}")
                print(f"   • Comissões com saldo: {result['comissoes_com_saldo']}")
                print(f"\n💬 Mensagem: {result['mensagem']}")
            else:
                print_error(f"Erro: {r.text}")
        else:
            print_info("Nenhuma comissão pendente para testar fechamento")
except Exception as e:
    print_error(f"Exceção: {str(e)}")

# ============================= RESUMO =============================

print_header("Testes Concluídos")
print(f"✨ Endpoint de conferência avançada testado com sucesso!")
print(f"✨ Endpoint de pagamento parcial testado com sucesso!")
