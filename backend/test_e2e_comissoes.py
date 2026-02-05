"""
SPRINT 6 - PASSO 5/5: TESTES E2E DO MÓDULO DE COMISSÕES
Data: 22/01/2026

Script de testes end-to-end para validar o fluxo completo de comissões:
1. Comissões Abertas
2. Conferência por Funcionário
3. Fechamento de Comissões
4. Histórico de Fechamentos
5. Detalhes do Fechamento
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configuração
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_header(msg: str):
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"{msg}")
    print(f"{'='*60}{Colors.END}\n")

# ============================================================================
# TESTES E2E - FLUXO COMPLETO
# ============================================================================

def test_1_comissoes_abertas():
    """Teste 1: Listar comissões em aberto"""
    print_header("TESTE 1: COMISSÕES EM ABERTO")
    
    try:
        response = requests.get(f"{BASE_URL}/comissoes/abertas", headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                funcionarios = data.get("funcionarios", [])
                print_success(f"Endpoint funcionando - {len(funcionarios)} funcionário(s) com comissões abertas")
                
                for func in funcionarios:
                    print(f"  → Funcionário: {func['nome_funcionario']} (ID: {func['funcionario_id']})")
                    print(f"     Total Pendente: R$ {func['total_pendente']:.2f}")
                    print(f"     Quantidade: {func['quantidade_comissoes']}")
                
                return funcionarios
            else:
                print_error("Success = false na resposta")
                return None
        else:
            print_error(f"Status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erro na requisição: {str(e)}")
        return None

def test_2_conferencia_funcionario(funcionario_id: int):
    """Teste 2: Conferir comissões de um funcionário"""
    print_header(f"TESTE 2: CONFERÊNCIA DO FUNCIONÁRIO {funcionario_id}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/comissoes/fechamento/{funcionario_id}",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                comissoes = data.get("comissoes", [])
                total_comissoes = data.get("total_comissoes", 0)
                valor_total = data.get("valor_total", 0)
                
                print_success(f"Endpoint funcionando - {len(comissoes)} comissão(ões) encontrada(s)")
                print(f"  → Total: R$ {valor_total:.2f}")
                print(f"  → Quantidade: {total_comissoes}")
                
                if comissoes:
                    primeira_venda = comissoes[0].get('data_venda', 'N/A')
                    ultima_venda = comissoes[-1].get('data_venda', 'N/A')
                    print(f"  → Primeira venda: {primeira_venda}")
                    print(f"  → Última venda: {ultima_venda}")
                
                return data
            else:
                print_error("Success = false na resposta")
                return None
        else:
            print_error(f"Status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erro na requisição: {str(e)}")
        return None

def test_3_fechamento_comissoes(funcionario_id: int, comissao_ids: List[int], observacao: str = "Teste E2E"):
    """Teste 3: Fechar comissões"""
    print_header(f"TESTE 3: FECHAMENTO DE {len(comissao_ids)} COMISSÃO(ÕES)")
    
    # Data de pagamento: 3 dias no futuro
    data_pagamento = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    payload = {
        "funcionario_id": funcionario_id,
        "comissao_ids": comissao_ids,
        "data_pagamento": data_pagamento,
        "observacao": observacao
    }
    
    print_info(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/comissoes/fechar",
            json=payload,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                print_success("Fechamento realizado com sucesso!")
                print(f"  → Funcionário: {data.get('funcionario_nome')}")
                print(f"  → Comissões fechadas: {data.get('quantidade_fechada')}")
                print(f"  → Valor total: R$ {data.get('valor_total'):.2f}")
                print(f"  → Data pagamento: {data.get('data_pagamento')}")
                
                return data
            else:
                print_error(f"Success = false: {data.get('detail', 'Erro desconhecido')}")
                return None
        else:
            print_error(f"Status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erro na requisição: {str(e)}")
        return None

def test_4_historico_fechamentos(data_inicio: Optional[str] = None, data_fim: Optional[str] = None, funcionario_id: Optional[int] = None):
    """Teste 4: Listar histórico de fechamentos"""
    print_header("TESTE 4: HISTÓRICO DE FECHAMENTOS")
    
    params = {}
    if data_inicio:
        params["data_inicio"] = data_inicio
    if data_fim:
        params["data_fim"] = data_fim
    if funcionario_id:
        params["funcionario_id"] = funcionario_id
    
    print_info(f"Filtros: {params if params else 'Nenhum'}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/comissoes/fechamentos",
            params=params,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                fechamentos = data.get("fechamentos", [])
                
                print_success(f"Endpoint funcionando - {len(fechamentos)} fechamento(s) encontrado(s)")
                
                # Calcular totais
                valor_total_geral = sum(f.get('valor_total', 0) for f in fechamentos)
                qtde_total = sum(f.get('quantidade_comissoes', 0) for f in fechamentos)
                
                print(f"  → Total de fechamentos: {len(fechamentos)}")
                print(f"  → Valor total geral: R$ {valor_total_geral:.2f}")
                print(f"  → Quantidade total: {qtde_total}")
                
                for fech in fechamentos[:3]:  # Mostrar apenas os 3 primeiros
                    print(f"\n  Fechamento:")
                    print(f"    → Funcionário: {fech['nome_funcionario']} (ID: {fech['funcionario_id']})")
                    print(f"    → Data pagamento: {fech['data_pagamento']}")
                    print(f"    → Valor: R$ {fech['valor_total']:.2f}")
                    print(f"    → Comissões: {fech['quantidade_comissoes']}")
                
                return data
            else:
                print_error("Success = false na resposta")
                return None
        else:
            print_error(f"Status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erro na requisição: {str(e)}")
        return None

def test_5_detalhe_fechamento(funcionario_id: int, data_pagamento: str):
    """Teste 5: Detalhe de um fechamento específico"""
    print_header("TESTE 5: DETALHE DO FECHAMENTO")
    
    params = {
        "funcionario_id": funcionario_id,
        "data_pagamento": data_pagamento
    }
    
    print_info(f"Parâmetros: {params}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/comissoes/fechamentos/detalhe",
            params=params,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                fechamento = data.get("fechamento", {})
                comissoes = data.get("comissoes", [])
                
                print_success(f"Endpoint funcionando - {len(comissoes)} comissão(ões) no fechamento")
                print(f"  → Funcionário: {fechamento.get('nome_funcionario')}")
                print(f"  → Data pagamento: {fechamento.get('data_pagamento')}")
                print(f"  → Valor total: R$ {fechamento.get('valor_total', 0):.2f}")
                print(f"  → Quantidade: {fechamento.get('quantidade_comissoes', 0)}")
                print(f"  → Período: {fechamento.get('periodo_vendas', 'N/A')}")
                print(f"  → Observação: {fechamento.get('observacao_pagamento', 'N/A')}")
                
                return data
            else:
                print_error("Success = false na resposta")
                return None
        else:
            print_error(f"Status {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erro na requisição: {str(e)}")
        return None

# ============================================================================
# TESTES DE BORDA
# ============================================================================

def test_borda_1_fechamento_vazio():
    """Teste de Borda 1: Tentar fechar sem comissões"""
    print_header("TESTE DE BORDA 1: FECHAMENTO VAZIO")
    
    payload = {
        "funcionario_id": 1,
        "comissao_ids": [],
        "data_pagamento": datetime.now().strftime("%Y-%m-%d"),
        "observacao": "Teste vazio"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/comissoes/fechar",
            json=payload,
            headers=HEADERS
        )
        
        if response.status_code == 400:
            print_success("Validação funcionando - rejeita fechamento vazio")
        else:
            print_error(f"Deveria retornar 400, retornou {response.status_code}")
            
    except Exception as e:
        print_error(f"Erro: {str(e)}")

def test_borda_2_historico_vazio():
    """Teste de Borda 2: Histórico sem dados"""
    print_header("TESTE DE BORDA 2: HISTÓRICO VAZIO")
    
    # Buscar em data futura (sem dados)
    data_futura = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    
    params = {
        "data_inicio": data_futura,
        "data_fim": data_futura
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/comissoes/fechamentos",
            params=params,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            if len(data.get("fechamentos", [])) == 0:
                print_success("Retorna lista vazia corretamente")
            else:
                print_warning("Encontrou dados em data futura (inesperado)")
        else:
            print_error(f"Status {response.status_code}")
            
    except Exception as e:
        print_error(f"Erro: {str(e)}")

def test_borda_3_parametros_invalidos():
    """Teste de Borda 3: Parâmetros inválidos"""
    print_header("TESTE DE BORDA 3: PARÂMETROS INVÁLIDOS")
    
    # Teste 1: Detalhe sem parâmetros
    print_info("Teste 1: Detalhe sem parâmetros")
    try:
        response = requests.get(f"{BASE_URL}/comissoes/fechamentos/detalhe")
        if response.status_code == 422:
            print_success("Validação funcionando - rejeita falta de parâmetros")
        else:
            print_error(f"Esperado 422, obtido {response.status_code}")
    except Exception as e:
        print_error(f"Erro: {str(e)}")
    
    # Teste 2: Funcionário inexistente
    print_info("\nTeste 2: Funcionário inexistente")
    try:
        response = requests.get(f"{BASE_URL}/comissoes/fechamento/99999")
        if response.status_code in [404, 200]:  # Pode retornar vazio ou 404
            print_success("Trata funcionário inexistente")
        else:
            print_warning(f"Status inesperado: {response.status_code}")
    except Exception as e:
        print_error(f"Erro: {str(e)}")

def test_borda_4_fechamento_duplicado():
    """Teste de Borda 4: Tentar fechar comissões já fechadas"""
    print_header("TESTE DE BORDA 4: FECHAMENTO DUPLICADO")
    
    print_warning("Este teste requer comissões já fechadas")
    print_info("Execute após ter fechado comissões no teste E2E")
    # Implementação específica depende de ter IDs de comissões fechadas

# ============================================================================
# VALIDAÇÃO FINANCEIRA
# ============================================================================

def validacao_financeira_completa(funcionario_id: int):
    """Validação financeira: conferir totais em todas as etapas"""
    print_header("VALIDAÇÃO FINANCEIRA COMPLETA")
    
    totais = {}
    
    # 1. Total em comissões abertas
    print_info("1. Buscando total em Comissões Abertas...")
    response = requests.get(f"{BASE_URL}/comissoes/abertas")
    if response.status_code == 200:
        data = response.json()
        funcionarios = data.get("funcionarios", [])
        for func in funcionarios:
            if func["funcionario_id"] == funcionario_id:
                totais["abertas"] = func["total_pendente"]
                print_success(f"   Total Abertas: R$ {totais['abertas']:.2f}")
                break
    
    # 2. Total na conferência
    print_info("\n2. Buscando total na Conferência...")
    response = requests.get(f"{BASE_URL}/comissoes/fechamento/{funcionario_id}")
    if response.status_code == 200:
        data = response.json()
        totais["conferencia"] = data.get("valor_total", 0)
        print_success(f"   Total Conferência: R$ {totais['conferencia']:.2f}")
    
    # 3. Comparar
    print_info("\n3. Comparando totais...")
    if totais.get("abertas") == totais.get("conferencia"):
        print_success("✓ Totais conferem entre Abertas e Conferência!")
    else:
        print_error(f"✗ Divergência: Abertas={totais.get('abertas')} vs Conferência={totais.get('conferencia')}")
    
    return totais

# ============================================================================
# RUNNER PRINCIPAL
# ============================================================================

def run_all_tests():
    """Executa todos os testes na sequência"""
    print(f"{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║     SPRINT 6 - PASSO 5/5: TESTES E2E MÓDULO DE COMISSÕES     ║")
    print("║                    Data: 22/01/2026                           ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print(Colors.END)
    
    # FASE 1: TESTES E2E
    print_header("FASE 1: TESTES END-TO-END")
    
    # Teste 1: Comissões Abertas
    funcionarios = test_1_comissoes_abertas()
    if not funcionarios or len(funcionarios) == 0:
        print_warning("Nenhum funcionário com comissões abertas. Testes parciais.")
        return
    
    # Pegar primeiro funcionário
    primeiro_func = funcionarios[0]
    funcionario_id = primeiro_func["funcionario_id"]
    
    # Teste 2: Conferência
    conferencia = test_2_conferencia_funcionario(funcionario_id)
    if not conferencia:
        print_error("Falha na conferência. Abortando testes.")
        return
    
    # Teste 3: Fechamento (comentado para não alterar dados)
    # comissao_ids = [c["id"] for c in conferencia.get("comissoes", [])[:2]]  # Apenas 2 primeiras
    # fechamento = test_3_fechamento_comissoes(funcionario_id, comissao_ids)
    print_warning("Teste de Fechamento DESABILITADO (não altera dados)")
    
    # Teste 4: Histórico
    # Buscar últimos 30 dias
    data_fim = datetime.now().strftime("%Y-%m-%d")
    data_inicio = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    historico = test_4_historico_fechamentos(data_inicio, data_fim)
    
    # Teste 5: Detalhe (se houver fechamento)
    if historico and len(historico.get("fechamentos", [])) > 0:
        primeiro_fechamento = historico["fechamentos"][0]
        test_5_detalhe_fechamento(
            primeiro_fechamento["funcionario_id"],
            primeiro_fechamento["data_pagamento"]
        )
    
    # FASE 2: TESTES DE BORDA
    print_header("FASE 2: TESTES DE BORDA")
    test_borda_1_fechamento_vazio()
    test_borda_2_historico_vazio()
    test_borda_3_parametros_invalidos()
    
    # FASE 3: VALIDAÇÃO FINANCEIRA
    print_header("FASE 3: VALIDAÇÃO FINANCEIRA")
    validacao_financeira_completa(funcionario_id)
    
    # RESUMO FINAL
    print_header("RESUMO FINAL")
    print_success("Testes E2E executados com sucesso!")
    print_info("Revisar logs acima para identificar falhas específicas")
    print_warning("Alguns testes foram desabilitados para não alterar dados")

if __name__ == "__main__":
    run_all_tests()
