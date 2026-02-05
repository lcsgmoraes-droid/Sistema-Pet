"""
SPRINT 6 - PASSO 5/5: VALIDAÇÃO FINAL MANUAL
Testa todos os endpoints do módulo de comissões em ordem
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzM3NTc4NDAwfQ.test"}

def colorize(text, color):
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "end": "\033[0m"
    }
    return f"{colors.get(color, '')}{text}{colors['end']}"

print("="*80)
print(colorize("VALIDAÇÃO FINAL MANUAL DO MÓDULO DE COMISSÕES", "green"))
print("="*80)

passed = 0
failed = 0

# 1. COMISSÕES ABERTAS
print("\n1️⃣  TESTE: GET /comissoes/abertas")
try:
    r = requests.get(f"{BASE_URL}/comissoes/abertas", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        funcionarios = data.get('funcionarios', [])
        print(colorize(f"   ✅ Status 200 - {len(funcionarios)} funcionário(s) com comissões abertas", "green"))
        for f in funcionarios:
            print(f"      → {f['nome_funcionario']} (ID {f['funcionario_id']}): R$ {f['total_pendente']:.2f}")
        passed += 1
    else:
        print(colorize(f"   ❌ Status {r.status_code}: {r.text[:100]}", "red"))
        failed += 1
except Exception as e:
    print(colorize(f"   ❌ Exceção: {str(e)[:100]}", "red"))
    failed += 1

# 2. CONFERÊNCIA DO FUNCIONÁRIO
print("\n2️⃣  TESTE: GET /comissoes/fechamento/14")
try:
    r = requests.get(f"{BASE_URL}/comissoes/fechamento/14", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        print(colorize(f"   ✅ Status 200", "green"))
        print(f"      Funcionário: {data['funcionario']['nome']}")
        print(f"      Comissões: {data['total_comissoes']}")
        print(f"      Total: R$ {data['valor_total']:.2f}")
        passed += 1
    else:
        print(colorize(f"   ❌ Status {r.status_code}", "red"))
        failed += 1
except Exception as e:
    print(colorize(f"   ❌ Exceção: {str(e)[:100]}", "red"))
    failed += 1

# 3. HISTÓRICO DE FECHAMENTOS
print("\n3️⃣  TESTE: GET /comissoes/fechamentos")
try:
    r = requests.get(
        f"{BASE_URL}/comissoes/fechamentos",
        params={"data_inicio": "2026-01-01"},
        headers=HEADERS
    )
    if r.status_code == 200:
        data = r.json()
        fechamentos = data.get('fechamentos', [])
        print(colorize(f"   ✅ Status 200 - {len(fechamentos)} fechamento(s) encontrado(s)", "green"))
        for fech in fechamentos:
            print(f"      → {fech['nome_funcionario']} (ID {fech['funcionario_id']})")
            print(f"        Data: {fech['data_pagamento']} | Valor: R$ {fech['valor_total']:.2f} | Qtd: {fech['quantidade_comissoes']}")
        passed += 1
    else:
        print(colorize(f"   ❌ Status {r.status_code}: {r.text[:100]}", "red"))
        failed += 1
except Exception as e:
    print(colorize(f"   ❌ Exceção: {str(e)[:100]}", "red"))
    failed += 1

# 4. DETALHE DE UM FECHAMENTO
print("\n4️⃣  TESTE: GET /comissoes/fechamentos/detalhe")
try:
    r = requests.get(
        f"{BASE_URL}/comissoes/fechamentos/detalhe",
        params={"funcionario_id": 14, "data_pagamento": "2026-01-22"},
        headers=HEADERS
    )
    if r.status_code == 200:
        data = r.json()
        fechamento = data.get('fechamento', {})
        comissoes = data.get('comissoes', [])
        print(colorize(f"   ✅ Status 200", "green"))
        print(f"      Funcionário: {fechamento.get('nome_funcionario', 'N/A')}")
        print(f"      Comissões: {fechamento.get('quantidade_comissoes', len(comissoes))}")
        print(f"      Total: R$ {fechamento.get('valor_total', 0):.2f}")
        passed += 1
    else:
        print(colorize(f"   ❌ Status {r.status_code}: {r.text[:100]}", "red"))
        failed += 1
except Exception as e:
    print(colorize(f"   ❌ Exceção: {str(e)[:100]}", "red"))
    failed += 1

# 5. RESUMO FINANCEIRO
print("\n5️⃣  TESTE: GET /comissoes/resumo")
try:
    r = requests.get(
        f"{BASE_URL}/comissoes/resumo",
        params={"funcionario_id": 14},
        headers=HEADERS
    )
    if r.status_code == 200:
        data = r.json()
        resumo = data.get('resumo', {})
        print(colorize(f"   ✅ Status 200", "green"))
        print(f"      Total gerado: R$ {resumo.get('total_gerado', 0):.2f}")
        print(f"      Total pago: R$ {resumo.get('total_pago', 0):.2f}")
        print(f"      Total pendente: R$ {resumo.get('total_pendente', 0):.2f}")
        print(f"      Saldo a pagar: R$ {resumo.get('saldo_a_pagar', 0):.2f}")
        passed += 1
    else:
        print(colorize(f"   ❌ Status {r.status_code}", "red"))
        failed += 1
except Exception as e:
    print(colorize(f"   ❌ Exceção: {str(e)[:100]}", "red"))
    failed += 1

# RESUMO
print("\n" + "="*80)
print(colorize(f"RESUMO: {passed} PASSOU(ARAM) | {failed} FALHOU(ARAM)", "green" if failed == 0 else "yellow"))
print("="*80)
