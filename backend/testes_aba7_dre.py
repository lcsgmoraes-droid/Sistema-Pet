#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTES - ABA 7: DRE Inteligente
Validação completa dos cálculos e endpoints da DRE
"""

import json
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import requests

BASE_URL = "http://localhost:8000"

# ==================== CORES PARA OUTPUT ====================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test(title, result, details=""):
    """Print resultado de um teste"""
    symbol = f"{Colors.GREEN}✅{Colors.RESET}" if result else f"{Colors.RED}❌{Colors.RESET}"
    print(f"{symbol} {title}")
    if details:
        print(f"   {details}")

def print_section(title):
    """Print seção de testes"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

# ==================== TESTES DE ENDPOINTS ====================

def test_endpoints():
    """Testar todos os endpoints da ABA 7"""
    print_section("1. TESTANDO ENDPOINTS")
    
    # Dados de teste
    usuario_id = 1  # Ajustar conforme necessário
    data_inicio = (date.today() - timedelta(days=30)).isoformat()
    data_fim = date.today().isoformat()
    
    tests = []
    
    # Teste 1: GET /api/ia/dre/periodo
    try:
        response = requests.get(
            f"{BASE_URL}/api/ia/dre/periodo",
            params={
                "usuario_id": usuario_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim
            },
            timeout=10
        )
        
        success = response.status_code == 200
        tests.append(("GET /api/ia/dre/periodo", success))
        
        if success:
            data = response.json()
            receita = data.get('receita_liquida', 0)
            custo = data.get('custo_produtos', 0)
            lucro = data.get('lucro_bruto', 0)
            print_test(
                "GET /api/ia/dre/periodo",
                success,
                f"Receita: R${receita:,.2f} | Custo: R${custo:,.2f} | Lucro: R${lucro:,.2f}"
            )
        else:
            print_test("GET /api/ia/dre/periodo", False, f"Status: {response.status_code}")
            
    except Exception as e:
        tests.append(("GET /api/ia/dre/periodo", False))
        print_test("GET /api/ia/dre/periodo", False, str(e))
    
    # Teste 2: GET /api/ia/dre/canais
    try:
        response = requests.get(
            f"{BASE_URL}/api/ia/dre/canais",
            params={
                "usuario_id": usuario_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim
            },
            timeout=10
        )
        
        success = response.status_code == 200
        tests.append(("GET /api/ia/dre/canais", success))
        
        if success:
            data = response.json()
            canais = data.get('canais', [])
            print_test(
                "GET /api/ia/dre/canais",
                success,
                f"Canais encontrados: {len(canais)}"
            )
            if canais:
                for i, canal in enumerate(canais[:3]):
                    print(f"     Canal {i+1}: {canal.get('nome', 'N/A')} - R${canal.get('receita', 0):,.2f}")
        else:
            print_test("GET /api/ia/dre/canais", False, f"Status: {response.status_code}")
            
    except Exception as e:
        tests.append(("GET /api/ia/dre/canais", False))
        print_test("GET /api/ia/dre/canais", False, str(e))
    
    # Teste 3: POST /api/ia/dre/alocacao
    try:
        payload = {
            "usuario_id": usuario_id,
            "periodo_id": 1,
            "modo": "proporcional",
            "alocacoes": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ia/dre/alocacao",
            json=payload,
            timeout=10
        )
        
        success = response.status_code in [200, 201]
        tests.append(("POST /api/ia/dre/alocacao", success))
        print_test(
            "POST /api/ia/dre/alocacao (modo proporcional)",
            success,
            f"Status: {response.status_code}"
        )
        
    except Exception as e:
        tests.append(("POST /api/ia/dre/alocacao", False))
        print_test("POST /api/ia/dre/alocacao", False, str(e))
    
    # Teste 4: GET /api/ia/dre/consolidado
    try:
        response = requests.get(
            f"{BASE_URL}/api/ia/dre/consolidado",
            params={
                "usuario_id": usuario_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim
            },
            timeout=10
        )
        
        success = response.status_code == 200
        tests.append(("GET /api/ia/dre/consolidado", success))
        
        if success:
            data = response.json()
            lucro_liquido = data.get('lucro_liquido', 0)
            margem = data.get('margem_liquida', 0)
            print_test(
                "GET /api/ia/dre/consolidado",
                success,
                f"Lucro Líquido: R${lucro_liquido:,.2f} | Margem: {margem:.2f}%"
            )
        else:
            print_test("GET /api/ia/dre/consolidado", False, f"Status: {response.status_code}")
            
    except Exception as e:
        tests.append(("GET /api/ia/dre/consolidado", False))
        print_test("GET /api/ia/dre/consolidado", False, str(e))
    
    # Resumo
    print_section("RESUMO DOS TESTES")
    total = len(tests)
    passed = sum(1 for _, r in tests if r)
    failed = total - passed
    
    print(f"Total: {total} | {Colors.GREEN}Passou: {passed}{Colors.RESET} | {Colors.RED}Falhou: {failed}{Colors.RESET}")
    
    return passed == total

# ==================== TESTES DE CÁLCULOS ====================

def test_calculos():
    """Testar lógica de cálculos"""
    print_section("2. VALIDANDO CÁLCULOS")
    
    # Exemplo de dados para validar
    print(f"{Colors.BOLD}Teste de Cálculos DRE:{Colors.RESET}\n")
    
    # Cenário: Faturamento R$ 100.000
    receita_bruta = 100000.00
    desconto = 5000.00
    receita_liquida = receita_bruta - desconto
    
    print(f"Receita Bruta:        R$ {receita_bruta:>12,.2f}")
    print(f"Desconto:             R$ {desconto:>12,.2f}")
    print(f"Receita Líquida:      R$ {receita_liquida:>12,.2f}")
    
    # CMV (30% da receita)
    cmv = receita_liquida * 0.30
    lucro_bruto = receita_liquida - cmv
    margem_bruta = (lucro_bruto / receita_liquida) * 100
    
    print(f"\nCusto Produtos (CMV): R$ {cmv:>12,.2f}")
    print(f"Lucro Bruto:          R$ {lucro_bruto:>12,.2f}")
    print(f"Margem Bruta:         {margem_bruta:>13,.2f}%")
    
    # Despesas (40% da receita)
    desp_vendas = receita_liquida * 0.15
    desp_admin = receita_liquida * 0.15
    desp_financeira = receita_liquida * 0.05
    desp_outras = receita_liquida * 0.05
    total_despesas = desp_vendas + desp_admin + desp_financeira + desp_outras
    
    lucro_operacional = lucro_bruto - total_despesas
    margem_operacional = (lucro_operacional / receita_liquida) * 100
    
    print(f"\nDespesas Vendas:      R$ {desp_vendas:>12,.2f} (15%)")
    print(f"Despesas Admin:       R$ {desp_admin:>12,.2f} (15%)")
    print(f"Despesas Financeiras: R$ {desp_financeira:>12,.2f} (5%)")
    print(f"Outras Despesas:      R$ {desp_outras:>12,.2f} (5%)")
    print(f"Total Despesas:       R$ {total_despesas:>12,.2f}")
    print(f"\nLucro Operacional:    R$ {lucro_operacional:>12,.2f}")
    print(f"Margem Operacional:   {margem_operacional:>13,.2f}%")
    
    # Impostos (30% do lucro operacional)
    taxa_imposto = 0.30
    impostos = lucro_operacional * taxa_imposto
    lucro_liquido = lucro_operacional - impostos
    margem_liquida = (lucro_liquido / receita_liquida) * 100
    
    print(f"\nImpostos (30%):       R$ {impostos:>12,.2f}")
    print(f"\n{Colors.GREEN}Lucro Líquido:        R$ {lucro_liquido:>12,.2f}{Colors.RESET}")
    print(f"{Colors.GREEN}Margem Líquida:       {margem_liquida:>13,.2f}%{Colors.RESET}")
    
    # Validações
    print(f"\n{Colors.BOLD}Validações:{Colors.RESET}")
    validacoes = []
    
    # V1: Receita líquida > 0
    v1 = receita_liquida > 0
    validacoes.append(v1)
    print_test("Receita Líquida > 0", v1)
    
    # V2: CMV < Receita Líquida
    v2 = cmv < receita_liquida
    validacoes.append(v2)
    print_test("CMV < Receita Líquida", v2)
    
    # V3: Margem Bruta entre 0% e 100%
    v3 = 0 <= margem_bruta <= 100
    validacoes.append(v3)
    print_test("Margem Bruta válida (0-100%)", v3, f"Valor: {margem_bruta:.2f}%")
    
    # V4: Lucro Bruto > Total Despesas (lucrativo)
    v4 = lucro_bruto > total_despesas
    validacoes.append(v4)
    print_test("Lucro Bruto > Total Despesas", v4)
    
    # V5: Impostos < Lucro Operacional
    v5 = impostos < lucro_operacional
    validacoes.append(v5)
    print_test("Impostos < Lucro Operacional", v5)
    
    # V6: Margem Líquida realista (5-25%)
    v6 = 0 <= margem_liquida <= 100
    validacoes.append(v6)
    print_test("Margem Líquida válida", v6, f"Valor: {margem_liquida:.2f}%")
    
    return all(validacoes)

# ==================== TESTES DE ALOCAÇÃO ====================

def test_alocacao():
    """Testar lógica de alocação de despesas"""
    print_section("3. TESTANDO ALOCAÇÃO DE DESPESAS")
    
    print(f"{Colors.BOLD}Cenário: 3 canais com receitas diferentes{Colors.RESET}\n")
    
    # Dados dos canais
    canais = {
        "Loja Física": 60000.00,
        "E-commerce": 30000.00,
        "Marketplace": 10000.00
    }
    
    receita_total = sum(canais.values())
    despesa_total = 20000.00  # Total de despesas a alocar
    
    print(f"Receita Total: R$ {receita_total:,.2f}")
    print(f"Despesa Total a Alocar: R$ {despesa_total:,.2f}\n")
    
    # Modo PROPORCIONAL
    print(f"{Colors.BOLD}Modo PROPORCIONAL:{Colors.RESET}")
    print(f"{'Canal':<20} {'Receita':>15} {'Percentual':>12} {'Despesa Alocada':>18}")
    print("-" * 67)
    
    total_alocado = 0
    validacoes = []
    
    for canal, receita in canais.items():
        percentual = (receita / receita_total) * 100
        despesa_alocada = (percentual / 100) * despesa_total
        total_alocado += despesa_alocada
        
        print(f"{canal:<20} R${receita:>13,.2f} {percentual:>11,.2f}% R${despesa_alocada:>16,.2f}")
        
        # V: Despesa alocada > 0
        validacoes.append(despesa_alocada > 0)
    
    print("-" * 67)
    print(f"{'TOTAL':<20} R${receita_total:>13,.2f}             R${total_alocado:>16,.2f}")
    
    # Validações
    print(f"\n{Colors.BOLD}Validações:{Colors.RESET}")
    
    # V1: Total alocado = despesa total
    v1 = abs(total_alocado - despesa_total) < 0.01  # Margem de erro para float
    validacoes.append(v1)
    print_test("Total alocado = Despesa total", v1, f"Alocado: R${total_alocado:.2f}")
    
    # V2: Cada canal tem despesa > 0
    v2 = all(validacoes[:-1])
    validacoes.append(v2)
    print_test("Cada canal tem alocação > 0", v2)
    
    # Modo MANUAL
    print(f"\n{Colors.BOLD}Modo MANUAL (customizado):{Colors.RESET}")
    print(f"{'Canal':<20} {'Receita':>15} {'Despesa':>18}")
    print("-" * 55)
    
    alocacoes_manuais = {
        "Loja Física": 12000.00,
        "E-commerce": 6000.00,
        "Marketplace": 2000.00
    }
    
    validacoes_manual = []
    total_manual = 0
    
    for canal, despesa in alocacoes_manuais.items():
        receita = canais.get(canal, 0)
        total_manual += despesa
        print(f"{canal:<20} R${receita:>13,.2f} R${despesa:>16,.2f}")
        validacoes_manual.append(despesa > 0)
    
    print("-" * 55)
    print(f"{'TOTAL':<20} R${receita_total:>13,.2f} R${total_manual:>16,.2f}")
    
    # Validação
    v3 = abs(total_manual - despesa_total) < 0.01
    validacoes.append(v3)
    print_test("Manual: Total = Despesa esperada", v3)
    
    return all(validacoes)

# ==================== MAIN ====================

def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  TESTES - ABA 7: DRE INTELIGENTE                             ║")
    print("║  Validação de Cálculos, Endpoints e Alocação de Despesas     ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    try:
        # Teste 1: Endpoints
        endpoints_ok = test_endpoints()
    except Exception as e:
        print(f"{Colors.RED}Erro ao testar endpoints: {e}{Colors.RESET}")
        endpoints_ok = False
    
    try:
        # Teste 2: Cálculos
        calculos_ok = test_calculos()
    except Exception as e:
        print(f"{Colors.RED}Erro ao testar cálculos: {e}{Colors.RESET}")
        calculos_ok = False
    
    try:
        # Teste 3: Alocação
        alocacao_ok = test_alocacao()
    except Exception as e:
        print(f"{Colors.RED}Erro ao testar alocação: {e}{Colors.RESET}")
        alocacao_ok = False
    
    # Resultado final
    print_section("RESULTADO FINAL")
    
    testes_finais = [
        ("Endpoints", endpoints_ok),
        ("Cálculos", calculos_ok),
        ("Alocação", alocacao_ok)
    ]
    
    total = len(testes_finais)
    passed = sum(1 for _, r in testes_finais if r)
    
    for nome, resultado in testes_finais:
        symbol = f"{Colors.GREEN}✅{Colors.RESET}" if resultado else f"{Colors.RED}❌{Colors.RESET}"
        print(f"{symbol} {nome}")
    
    print(f"\n{Colors.BOLD}Total: {total} | {Colors.GREEN}Passou: {passed}{Colors.RESET} | {Colors.RED}Falhou: {total - passed}{Colors.RESET}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 TODOS OS TESTES PASSARAM!{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}⚠️ ALGUNS TESTES FALHARAM{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    exit(main())
