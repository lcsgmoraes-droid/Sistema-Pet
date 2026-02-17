"""
EXEMPLO: Cálculo Completo de Margem com TODOS os Custos
========================================================

Demonstra como calcular a margem REAL de uma venda considerando:
✅ Custo dos produtos (preco_custo × quantidade)
✅ Taxa de entrega (receita)
✅ Custo operacional da entrega (despesa)
✅ Taxa da forma de pagamento
✅ Impostos (Simples Nacional, etc)
✅ Comissões (vendedor, entregador)
✅ Descontos
"""

import requests
from decimal import Decimal


# ===== CONFIGURAÇÃO =====
API_URL = "http://localhost:8000"
TOKEN = "seu_token_aqui"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


# ===== EXEMPLO 1: Venda Simples sem Entrega =====
def exemplo_venda_simples():
    """
    Venda de R$ 100 com custo de R$ 60
    Pagamento em dinheiro (sem taxa)
    Sem entrega
    """
    print("\n" + "="*60)
    print("EXEMPLO 1: Venda Simples no Balcão")
    print("="*60)
    
    payload = {
        "subtotal": 100.00,           # Valor dos produtos
        "custo_total": 60.00,          # Custo: R$ 60 (produto a R$ 30, quantidade 2)
        "desconto": 0,                 # Sem desconto
        "forma_pagamento_id": 1,       # Dinheiro (taxa 0%)
        "parcelas": 1,
        "taxa_entrega": 0,             # Sem entrega
        "custo_operacional_entrega": 0,
        "comissao_percentual": 0,      # Sem comissão
        "comissao_valor": 0
    }
    
    response = requests.post(
        f"{API_URL}/pdv/indicadores/analisar-venda",
        json=payload,
        headers=headers
    )
    
    if response.status_code == 200:
        resultado = response.json()
        print_resultado(payload, resultado)
    else:
        print(f"❌ Erro: {response.status_code} - {response.text}")


# ===== EXEMPLO 2: Venda com Entrega =====
def exemplo_venda_com_entrega():
    """
    Venda de R$ 100 + R$ 15 de entrega
    Empresa fica com R$ 5 da entrega
    Entregador fica com R$ 10 da entrega (comissão)
    Custo operacional: R$ 8 (combustível - SEMPRE da empresa)
    """
    print("\n" + "="*60)
    print("EXEMPLO 2: Venda com Entrega (Distribuição da Taxa)")
    print("="*60)
    
    payload = {
        "subtotal": 100.00,
        "custo_total": 60.00,
        "desconto": 5.00,              # Desconto de R$ 5
        "forma_pagamento_id": 2,       # PIX (taxa 0%)
        "parcelas": 1,
        "taxa_entrega_cobrada": 15.00,        # Cliente paga R$ 15
        "taxa_entrega_receita_empresa": 5.00, # Empresa fica com R$ 5
        # Diferença (R$ 10) vai pro entregador
        "custo_operacional_entrega": 8.00,    # Custo SEMPRE da empresa
        "comissao_percentual": 0,
        "comissao_valor": 0
    }
    
    response = requests.post(
        f"{API_URL}/pdv/indicadores/analisar-venda",
        json=payload,
        headers=headers
    )
    
    if response.status_code == 200:
        resultado = response.json()
        print_resultado(payload, resultado)
        print("\n💡 DISTRIBUIÇÃO DA ENTREGA:")
        print(f"   - Cliente paga: R$ {payload['taxa_entrega_cobrada']:.2f}")
        print(f"   - Empresa recebe (RECEITA): R$ {payload['taxa_entrega_receita_empresa']:.2f}")
        print(f"   - Entregador recebe (COMISSÃO): R$ {payload['taxa_entrega_cobrada'] - payload['taxa_entrega_receita_empresa']:.2f}")
        print(f"   - Custo operacional (DESPESA): R$ {payload['custo_operacional_entrega']:.2f}")
        resultado_entrega = payload['taxa_entrega_receita_empresa'] - payload['custo_operacional_entrega'] - (payload['taxa_entrega_cobrada'] - payload['taxa_entrega_receita_empresa'])
        print(f"   - Resultado da entrega: R$ {resultado_entrega:.2f}")
    else:
        print(f"❌ Erro: {response.status_code} - {response.text}")


# ===== EXEMPLO 3: Venda com Cartão Parcelado e Comissão =====
def exemplo_venda_completa():
    """
    Venda COMPLETA com todos os custos:
    - Produtos: R$ 200 (custo R$ 120)
    - Entrega: Cliente paga R$ 15, empresa fica com R$ 6, entregador R$ 9
    - Custo operacional: R$ 8
    - Cartão crédito 3x (taxa 4%)
    - Comissão vendedor: 2% sobre o total
    - Desconto: R$ 10
    """
    print("\n" + "="*60)
    print("EXEMPLO 3: Venda Completa com TODOS os Custos")
    print("="*60)
    
    payload = {
        "subtotal": 200.00,
        "custo_total": 120.00,         # Produtos custaram R$ 120
        "desconto": 10.00,
        "forma_pagamento_id": 4,       # Cartão de crédito
        "parcelas": 3,                 # 3x (taxa ~4%)
        "taxa_entrega_cobrada": 15.00,        # Cliente paga R$ 15
        "taxa_entrega_receita_empresa": 6.00, # Empresa fica com R$ 6
        # Entregador fica com R$ 9
        "custo_operacional_entrega": 8.00,    # Custo empresa R$ 8
        "comissao_percentual": 2.0,    # 2% de comissão vendedor
        "comissao_valor": 0
    }
    
    response = requests.post(
        f"{API_URL}/pdv/indicadores/analisar-venda",
        json=payload,
        headers=headers
    )
    
    if response.status_code == 200:
        resultado = response.json()
        print_resultado(payload, resultado)
        
        print("\n📊 ANÁLISE DETALHADA:")
        valores = resultado['valores']
        custos = resultado['custos']
        margens = resultado['margens']
         (receita empresa): R$ {valores['taxa_entrega_receita_empresa']:.2f}")
        print(f"   = TOTAL: R$ {valores['total_venda']:.2f}")
        
        print(f"\n   CUSTOS DIRETOS:")
        print(f"   ├─ Produtos: R$ {custos['custo_produtos']:.2f}")
        print(f"   ├─ Entrega operacional: R$ {custos['custo_operacional_entrega']:.2f}")
        print(f"   └─ Comissão entregador: R$ {custos['comissao_entregador']:.2f}")
        print(f"   = TOTAL: R$ {custos['custo_total']:.2f}")
        
        print(f"\n   LUCRO BRUTO: R$ {margens['lucro_bruto']:.2f} ({margens['margem_bruta_percentual']:.1f}%)")
        
        print(f"\n   CUSTOS FISCAIS/FINANCEIROS:")
        print(f"   ├─ Taxa cartão: R$ {custos['taxa_pagamento']:.2f}")
        print(f"   ├─ Impostos: R$ {custos['imposto']:.2f}")
        print(f"   └─ Comissão vendedor: R$ {custos['comissao_vendedor']:.2f}")
        print(f"   = TOTAL: R$ {custos['custos_fiscais_totais']:.2f}")
        
        print(f"\n   🎯 LUCRO LÍQUIDO: R$ {margens['lucro_liquido']:.2f} ({margens['margem_liquida_percentual']:.1f}%)")
        
        print(f"\n   💡 ANÁLISE DA ENTREGA:")
        print(f"   ├─ Cliente pagou: R$ {valores['taxa_entrega_cobrada']:.2f}")
        print(f"   ├─ Empresa recebeu: R$ {valores['taxa_entrega_receita_empresa']:.2f}")
        print(f"   ├─ Entregador recebeu: R$ {custos['comissao_entregador']:.2f}")
        print(f"   ├─ Custo operacional: R$ {custos['custo_operacional_entrega']:.2f}")
        resultado_entrega = valores['taxa_entrega_receita_empresa'] - custos['custo_operacional_entrega']
        print(f"   └─ Resultado entrega (empresa): R$ {resultado_entrega:.2f}
        print(f"   = TOTAL: R$ {custos['custos_fiscais_totais']:.2f}")
        
        print(f"\n   🎯 LUCRO LÍQUIDO: R$ {margens['lucro_liquido']:.2f} ({margens['margem_liquida_percentual']:.1f}%)")
        
        status = resultado['status']
        print(f"\n   {status['icone']} STATUS: {status['status'].upper()}")
    Empresa dá TODA a taxa de entrega pro entregador!
    """
    print("\n" + "="*60)
    print("EXEMPLO 4: ⚠️ Venda com Margem BAIXA")
    print("="*60)
    
    payload = {
        "subtotal": 100.00,
        "custo_total": 75.00,          # Custo alto: 75% do valor
        "desconto": 5.00,              # Ainda dá desconto
        "forma_pagamento_id": 4,       # Cartão 12x (taxa alta ~8%)
        "parcelas": 12,
        "taxa_entrega_cobrada": 10.00,
        "taxa_entrega_receita_empresa": 0.00,  # Empresa NÃO fica com nada!
        # Entregador fica com os R$ 10 todos
        "custo_operacional_entrega": 8.00,  # E ainda tem custo operacional
    
    payload = {
        "subtotal": 100.00,
        "custo_total": 75.00,          # Custo alto: 75% do valor
        "desconto": 5.00,              # Ainda dá desconto
        "forma_pagamento_id": 4,       # Cartão 12x (taxa alta ~8%)
        "parcelas": 12,
        "taxa_entrega": 10.00,
        "custo_operacional_entrega": 8.00,  # Entrega quase sem lucro
        "comissao_percentual": 3.0,    # 3% de comissão
        "comissao_valor": 0
    }
    
    respcustos = resultado['custos']
        print(f"   Esta venda tem margem líquida de apenas {margens['margem_liquida_percentual']:.1f}%")
        print(f"   Lucro líquido: R$ {margens['lucro_liquido']:.2f}")
        print(f"\n   Problema: Empresa deu TODA a taxa de entrega pro entregador!")
        print(f"   - Cliente pagou R$ {resultado['valores']['taxa_entrega_cobrada']:.2f}")
        print(f"   - Entregador levou R$ {custos['comissao_entregador']:.2f}")
        print(f"   - Empresa ainda pagou R$ {custos['custo_operacional_entrega']:.2f} de custo")
        print(f"   - Prejuízo da entrega: R$ {custos['custo_operacional_entrega']:.2f}")
        print(f"\n   Considere:")
        print(f"   - Empresa ficar com parte da taxa de entrega")
        print(f"   - Reduzir desconto")
        print(f"   - Oferecer à vista ou menos parcela
    if response.status_code == 200:
        resultado = response.json()
        print_resultado(payload, resultado)
        
        print("\n⚠️ ALERTA:")
        margens = resultado['margens']
        print(f"   Esta venda tem margem líquida de apenas {margens['margem_liquida_percentual']:.1f}%")
        print(f"   Lucro líquido: R$ {margens['lucro_liquido']:.2f}")
        print(f"   Considere:")
        print(f"   - Reduzir desconto")
        print(f"   - Oferecer à vista ou menos parcelas")
        print(f"   - Revisar política de comissões")
    else:
        print(f"❌ Erro: {response.status_code} - {response.text}")
.get('taxa_entrega_cobrada', 0) > 0:
        print(f"   Taxa entrega (cobrada): R$ {payload['taxa_entrega_cobrada']:.2f}")
        print(f"   Taxa entrega (empresa): R$ {payload['taxa_entrega_receita_empresa']:.2f}")
        print(f"   Taxa entrega (entregador): R$ {payload['taxa_entrega_cobrada'] - payload['taxa_entrega_receita_empresa']:.2f}")
        print(f"   Custo operacional: R$ {payload['custo_operacional_entrega']:.2f}")
    if payload.get('comissao_percentual', 0) > 0:
        print(f"   Comissão vendedor: {payload['comissao_percentual']}%")
    
    print("\n📤 RESPONSE:")
    valores = resultado['valores']
    margens = resultado['margen] > 0:
        print(f"   Taxa entrega: R$ {payload['taxa_entrega']:.2f}")
        print(f"   Custo entrega: R$ {payload['custo_operacional_entrega']:.2f}")
    if payload['comissao_percentual'] > 0:
        print(f"   Comissão: {payload['comissao_percentual']}%")
    
    print("\n📤 RESPONSE:")
    valores = resultado['valores']
    margens = resultado['margens']
    custos = resultado['custos']
    status = resultado['status']
    
    print(f"   Total venda: R$ {valores['total_venda']:.2f}")
    print(f"   Margem bruta: {margens['margem_bruta_percentual']:.1f}%")
    print(f"   Margem líquida: {margens['margem_liquida_percentual']:.1f}%")
    print(f"   Lucro líquido: R$ {margens['lucro_liquido']:.2f}")
    print(f"   Status: {status['icone']} {status['status'].upper()}")


# ===== EXECUÇÃO =====
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║  EXEMPLOS DE CÁLCULO DE MARGEM COM TODOS OS CUSTOS          ║
║                                                              ║
║  ✅ Custo produtos (preço_custo × quantidade)               ║
║  ✅ Taxa de entrega (receita)                               ║
║  ✅ Custo operacional entrega (combustível, tempo)          ║
║  ✅ Taxa forma de pagamento (cartão, PIX)                   ║
║  ✅ Impostos (Simples Nacional, etc)                        ║
║  ✅ Comissões (vendedor, entregador)                        ║
║  ✅ Descontos                                               ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Executa exemplos
    exemplo_venda_simples()
    exemplo_venda_com_entrega()
    exemplo_venda_completa()
    exemplo_venda_margem_baixa()
    
    print("\n" + "="*60)
    print("✅ Exemplos executados com sucesso!")
    print("="*60)
    print("\n💡 Use esses padrões no seu PDV para garantir")
    print("   que TODAS as vendas sejam realmente lucrativas!\n")
