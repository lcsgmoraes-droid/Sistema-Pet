"""
Rotas para análise de indicadores no PDV
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.utils.pdv_indicadores import calcular_indicadores_venda, calcular_indicadores_item, calcular_sugestao_pix
from app.utils.logger import logger

router = APIRouter(prefix="/pdv/indicadores", tags=["PDV - Indicadores"])


# ===== SCHEMAS =====

class AnaliseVendaRequest(BaseModel):
    subtotal: float
    custo_total: float
    desconto: float = 0
    forma_pagamento_id: Optional[int] = None
    parcelas: int = 1
    taxa_entrega_cobrada: float = 0
    taxa_entrega_receita_empresa: float = 0
    custo_operacional_entrega: float = 0
    comissao_percentual: float = 0
    comissao_valor: float = 0


class AnaliseItemRequest(BaseModel):
    preco_venda: float
    preco_custo: float
    quantidade: int = 1


# ===== ENDPOINTS =====

@router.post("/analisar-venda")
def analisar_venda(
    request: AnaliseVendaRequest,
    user_tenant: tuple = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Analisa uma venda completa considerando TODOS os custos
    
    Custos considerados:
    - Custo dos produtos (preco_custo * quantidade)
    - Custo operacional da entrega (combustível - SEMPRE da empresa)
    - Comissão do entregador (parte da taxa de entrega que vai pro entregador)
    - Taxa da forma de pagamento (cartão, PIX, etc)
    - Impostos (Simples Nacional, Lucro Presumido, etc)
    - Comissões de vendedor
    - Descontos dados na venda
    
    Taxa de Entrega:
    - taxa_entrega_cobrada: Valor cobrado do cliente (ex: R$ 15)
    - taxa_entrega_receita_empresa: Quanto FICA com a empresa (ex: R$ 5)
    - Diferença (R$ 10) = Comissão do entregador (despesa)
    
    Retorna:
    - Valores detalhados: receita total, custos por categoria
    - Margens: bruta (receita - custos) e líquida (após impostos/taxas)
    - Status: 🟢 Saudável / 🟡 Alerta / 🔴 Crítico
    - Detalhamento de todas as taxas aplicadas
    """
    user, tenant_id = user_tenant
    
    try:
        resultado = calcular_indicadores_venda(
            db=db,
            tenant_id=tenant_id,
            subtotal=request.subtotal,
            custo_total=request.custo_total,
            desconto=request.desconto,
            forma_pagamento_id=request.forma_pagamento_id,
            parcelas=request.parcelas,
            taxa_entrega_cobrada=request.taxa_entrega_cobrada,
            taxa_entrega_receita_empresa=request.taxa_entrega_receita_empresa,
            custo_operacional_entrega=request.custo_operacional_entrega,
            comissao_percentual=request.comissao_percentual,
            comissao_valor=request.comissao_valor
        )
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao analisar venda: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analisar-item")
def analisar_item(
    request: AnaliseItemRequest,
    user_tenant: tuple = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Analisa um item individual
    Use enquanto adiciona produtos no PDV para alertar sobre margem baixa
    
    Retorna:
    - Valores do item
    - Margem bruta e estimada (com imposto)
    - Status do item
    """
    user, tenant_id = user_tenant
    
    try:
        resultado = calcular_indicadores_item(
            db=db,
            tenant_id=tenant_id,
            preco_venda=request.preco_venda,
            preco_custo=request.preco_custo,
            quantidade=request.quantidade
        )
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao analisar item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/referencias")
def get_referencias_margem(
    user_tenant: tuple = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Retorna os valores de referência de margem configurados
    para exibir no PDV
    """
    user, tenant_id = user_tenant
    
    from app.empresa_config_geral_models import EmpresaConfigGeral
    
    config = db.query(EmpresaConfigGeral).filter(
        EmpresaConfigGeral.tenant_id == tenant_id
    ).first()
    
    if config:
        return {
            'margem_saudavel_minima': float(config.margem_saudavel_minima),
            'margem_alerta_minima': float(config.margem_alerta_minima),
            'aliquota_imposto_padrao': float(config.aliquota_imposto_padrao),
            'mensagens': {
                'saudavel': config.mensagem_venda_saudavel,
                'alerta': config.mensagem_venda_alerta,
                'critica': config.mensagem_venda_critica
            }
        }
    else:
        # Valores padrão
        return {
            'margem_saudavel_minima': 30.0,
            'margem_alerta_minima': 15.0,
            'aliquota_imposto_padrao': 7.0,
            'mensagens': {
                'saudavel': '✅ Venda Saudável! Margem excelente.',
                'alerta': '⚠️ ATENÇÃO: Margem reduzida! Revisar preço.',
                'critica': '🚨 CRÍTICO: Margem muito baixa! Venda com prejuízo!'
            }
        }

class SugestaoPIXRequest(BaseModel):
    total_venda: float
    custo_total: float
    desconto_atual: float = 0
    aliquota_imposto: float = 7.0
    taxa_cartao_pct: float = 0.0  # taxa da forma de pagamento selecionada (ex: 3.5 para 3.5%)


@router.post("/sugestao-pix")
def sugestao_pix(
    request: SugestaoPIXRequest,
    user_tenant: tuple = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Calcula desconto máximo viável para oferecer ao cliente se ele pagar no PIX.
    A loja usa a economia da taxa zero do PIX para gerar atrativo ao cliente
    sem comprometer a margem mínima configurada.
    """
    user, tenant_id = user_tenant
    try:
        resultado = calcular_sugestao_pix(
            db=db,
            tenant_id=str(tenant_id),
            total_venda=request.total_venda,
            custo_total=request.custo_total,
            desconto_atual=request.desconto_atual,
            aliquota_imposto=request.aliquota_imposto,
            taxa_cartao_pct=request.taxa_cartao_pct,
        )
        return resultado
    except Exception as e:
        logger.error(f"Erro ao calcular sugestão PIX: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))