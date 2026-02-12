"""
Utilitário para cálculo de indicadores de venda no PDV
Analisa margem, impostos e classifica venda como saudável/alerta/crítico
"""

from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.empresa_config_geral_models import EmpresaConfigGeral
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.formas_pagamento_models import FormaPagamentoTaxa, ConfiguracaoImposto
from app.financeiro_models import FormaPagamento


def calcular_indicadores_venda(
    db: Session,
    tenant_id: str,
    subtotal: float,
    custo_total: float,
    desconto: float = 0,
    forma_pagamento_id: Optional[int] = None,
    parcelas: int = 1,
    taxa_entrega_cobrada: float = 0,
    taxa_entrega_receita_empresa: float = 0,
    custo_operacional_entrega: float = 0,
    comissao_percentual: float = 0,
    comissao_valor: float = 0
) -> Dict:
    """
    Calcula os indicadores de uma venda para exibição no PDV
    Considera TODOS os custos: produtos, entrega, comissões, impostos e taxas
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        subtotal: Valor bruto da venda (produtos sem desconto)
        custo_total: Custo total dos produtos (preco_custo * quantidade de cada item)
        desconto: Desconto aplicado na venda
        forma_pagamento_id: ID da forma de pagamento
        parcelas: Número de parcelas (se cartão crédito)
        taxa_entrega_cobrada: Valor COBRADO do cliente pela entrega (ex: R$ 15)
        taxa_entrega_receita_empresa: Valor que FICA com a empresa (ex: R$ 5)
            - Diferença vai para comissão do entregador
            - Se igual a taxa_cobrada, empresa fica com tudo
            - Se zero, entregador fica com tudo
        custo_operacional_entrega: Custo SEMPRE da empresa (combustível, etc)
        comissao_percentual: % de comissão sobre o total da venda
        comissao_valor: Valor fixo de comissão (alternativa ao %)
    
    Returns:
        dict com análise completa da venda incluindo todos os custos
    """
    
    # ========== CÁLCULO DE RECEITA ==========
    # Receita = produtos + o que REALMENTE fica com a empresa da entrega
    valor_produtos = subtotal - desconto
    receita_entrega_empresa = taxa_entrega_receita_empresa  # O que REALMENTE entra
    total_venda = valor_produtos + receita_entrega_empresa
    
    # ========== DISTRIBUIÇÃO DA TAXA DE ENTREGA ==========
    # Taxa cobrada - Receita empresa = Comissão do entregador
    taxa_entrega_comissao_entregador = taxa_entrega_cobrada - taxa_entrega_receita_empresa
    
    # ========== CÁLCULO DE CUSTOS ==========
    # Custo Total = produtos + operacional entrega + comissão entregador
    custo_total_real = custo_total + custo_operacional_entrega + taxa_entrega_comissao_entregador
    
    # Busca configuração da empresa
    config = db.query(EmpresaConfigGeral).filter(
        EmpresaConfigGeral.tenant_id == tenant_id
    ).first()
    
    # Valores padrão se não houver configuração
    margem_saudavel = float(config.margem_saudavel_minima) if config else 30.0
    margem_alerta = float(config.margem_alerta_minima) if config else 15.0
    aliquota_imposto = float(config.aliquota_imposto_padrao) if config else 7.0
    
    # Calcula taxa da forma de pagamento
    taxa_percentual = 0.0
    taxa_valor = 0.0
    forma_pagamento_nome = "Não informada"
    
    if forma_pagamento_id:
        forma_pag = db.query(FormaPagamento).filter(
            FormaPagamento.id == forma_pagamento_id
        ).first()
        
        if forma_pag:
            forma_pagamento_nome = forma_pag.nome
            
            # Busca taxa específica para o número de parcelas
            taxa_obj = db.query(FormaPagamentoTaxa).filter(
                FormaPagamentoTaxa.forma_pagamento_id == forma_pagamento_id,
                FormaPagamentoTaxa.parcelas == parcelas
            ).first()
            
            if taxa_obj:
                taxa_percentual = float(taxa_obj.taxa_percentual)
                taxa_valor = total_venda * (taxa_percentual / 100)
    
    # ========== CÁLCULO DE IMPOSTOS ==========
    imposto_valor = total_venda * (aliquota_imposto / 100)
    
    # ========== CÁLCULO DE COMISSÕES ==========
    # Usa comissão percentual OU valor fixo (o que for maior)
    comissao_calculada = total_venda * (comissao_percentual / 100)
    comissao_final = max(comissao_calculada, comissao_valor)
    
    # ========== CÁLCULO DE MARGENS ==========
    # Lucro Bruto = Receita Total - Custo Total (produtos + entrega)
    lucro_bruto = total_venda - custo_total_real
    
    # Lucro Líquido = Lucro Bruto - Todos os custos fiscais/financeiros
    lucro_liquido = lucro_bruto - taxa_valor - imposto_valor - comissao_final
    
    # Valor que efetivamente entra no caixa
    valor_liquido = total_venda - taxa_valor - imposto_valor - comissao_final
    
    # Percentuais
    margem_bruta_percentual = (lucro_bruto / total_venda * 100) if total_venda > 0 else 0
    margem_liquida_percentual = (lucro_liquido / total_venda * 100) if total_venda > 0 else 0
    
    # Classifica a venda baseado na margem LÍQUIDA
    if config:
        status = config.calcular_status_margem(margem_liquida_percentual)
    else:
        # Status padrão
        if margem_liquida_percentual >= margem_saudavel:
            status = {
                'status': 'saudavel',
                'mensagem': '✅ Venda Saudável! Margem excelente.',
                'cor': 'success',
                'icone': '✅'
            }
        elif margem_liquida_percentual >= margem_alerta:
            status = {
                'status': 'alerta',
                'mensagem': '⚠️ ATENÇÃO: Margem reduzida! Revisar preço.',
                'cor': 'warning',
                'icone': '⚠️'
            }
    
    return {
        'valores': {
            'subtotal': round(subtotal, 2),
            'desconto': round(desconto, 2),
            'valor_produtos': round(valor_produtos, 2),
            'taxa_entrega_cobrada': round(taxa_entrega_cobrada, 2),
            'taxa_entrega_receita_empresa': round(receita_entrega_empresa, 2),
            'total_venda': round(total_venda, 2),
            'valor_liquido': round(valor_liquido, 2)
        },
        'custos': {
            'custo_produtos': round(custo_total, 2),
            'custo_operacional_entrega': round(custo_operacional_entrega, 2),
            'comissao_entregador': round(taxa_entrega_comissao_entregador, 2),
            'custo_total': round(custo_total_real, 2),
            'taxa_pagamento': round(taxa_valor, 2),
            'imposto': round(imposto_valor, 2),
            'comissao_vendedor': round(comissao_final, 2),
            'custos_fiscais_totais': round(taxa_valor + imposto_valor + comissao_final, 2)
        },
        'margens': {
            'lucro_bruto': round(lucro_bruto, 2),
            'lucro_liquido': round(lucro_liquido, 2),
            'margem_bruta_percentual': round(margem_bruta_percentual, 2),
            'margem_liquida_percentual': round(margem_liquida_percentual, 2)
        },
        'detalhamento_taxas': {
            'forma_pagamento': forma_pagamento_nome,
            'parcelas': parcelas,
            'taxa_percentual': taxa_percentual,
            'aliquota_imposto': aliquota_imposto,
            'comissao_percentual': comissao_percentual
        },
        'taxas': {
            'forma_pagamento': forma_pagamento_nome,
            'parcelas': parcelas,
            'taxa_percentual': taxa_percentual,
            'taxa_valor': round(taxa_valor, 2),
            'aliquota_imposto': aliquota_imposto,
            'imposto_valor': round(imposto_valor, 2)
        },
        'status': status,
        'referencias': {
            'margem_saudavel_minima': margem_saudavel,
            'margem_alerta_minima': margem_alerta
        }
    }


def calcular_indicadores_item(
    db: Session,
    tenant_id: str,
    preco_venda: float,
    preco_custo: float,
    quantidade: int = 1
) -> Dict:
    """
    Calcula indicadores de um item individual
    Útil para mostrar no PDV enquanto adiciona produtos
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        preco_venda: Preço de venda unitário
        preco_custo: Preço de custo unitário
        quantidade: Quantidade do item
    
    Returns:
        dict com análise do item
    """
    
    total_venda = preco_venda * quantidade
    total_custo = preco_custo * quantidade
    
    # Busca configuração
    config = db.query(EmpresaConfigGeral).filter(
        EmpresaConfigGeral.tenant_id == tenant_id
    ).first()
    
    aliquota_imposto = float(config.aliquota_imposto_padrao) if config else 7.0
    
    # Calcula margem bruta (sem taxas de pagamento)
    lucro_bruto = total_venda - total_custo
    margem_bruta_percentual = (lucro_bruto / total_venda * 100) if total_venda > 0 else 0
    
    # Margem estimada (considera imposto, mas não taxa de pagamento)
    imposto_valor = total_venda * (aliquota_imposto / 100)
    lucro_estimado = lucro_bruto - imposto_valor
    margem_estimada_percentual = (lucro_estimado / total_venda * 100) if total_venda > 0 else 0
    
    # Status baseado na margem estimada
    if config:
        status = config.calcular_status_margem(margem_estimada_percentual)
    else:
        margem_saudavel = 30.0
        margem_alerta = 15.0
        
        if margem_estimada_percentual >= margem_saudavel:
            status = {'status': 'saudavel', 'icone': '✅', 'cor': 'success'}
        elif margem_estimada_percentual >= margem_alerta:
            status = {'status': 'alerta', 'icone': '⚠️', 'cor': 'warning'}
        else:
            status = {'status': 'critico', 'icone': '🚨', 'cor': 'danger'}
    
    return {
        'preco_venda': preco_venda,
        'preco_custo': preco_custo,
        'quantidade': quantidade,
        'total_venda': round(total_venda, 2),
        'total_custo': round(total_custo, 2),
        'lucro_bruto': round(lucro_bruto, 2),
        'margem_bruta_percentual': round(margem_bruta_percentual, 2),
        'imposto_estimado': round(imposto_valor, 2),
        'lucro_estimado': round(lucro_estimado, 2),
        'margem_estimada_percentual': round(margem_estimada_percentual, 2),
        'status': status
    }
