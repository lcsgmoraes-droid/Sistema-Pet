"""
Rotas para Dashboard Financeiro
Endpoints para dados consolidados do sistema
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import Optional
import logging

from uuid import UUID
from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User
from app.tenancy.context import get_current_tenant
from .vendas_models import Venda, VendaPagamento
from .financeiro_models import ContaReceber, ContaPagar
from .caixa_models import Caixa
from .produtos_models import Produto

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard/resumo")
async def obter_resumo_dashboard(
    periodo_dias: int = 30,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna resumo consolidado para o dashboard financeiro
    """
    current_user, tenant_id = user_and_tenant
    try:
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)
        
        # ========================================
        # 1. SALDO ATUAL (Baseado em vendas pagas)
        # ========================================
        vendas_pagas = db.query(
            func.sum(Venda.total)
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.status == 'finalizada'
            )
        ).scalar() or 0
        
        contas_pagas_total = db.query(
            func.sum(ContaPagar.valor_pago)
        ).filter(
            ContaPagar.tenant_id == tenant_id
        ).scalar() or 0
        
        saldo_atual = vendas_pagas - contas_pagas_total
        
        # ========================================
        # 2. CONTAS A RECEBER
        # ========================================
        contas_receber_total = db.query(
            func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido)
        ).filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status.in_(['pendente', 'parcial', 'vencida'])
            )
        ).scalar() or 0
        
        # Contas vencidas a receber
        contas_receber_vencidas = db.query(
            func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido)
        ).filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status.in_(['pendente', 'parcial', 'vencida']),
                ContaReceber.data_vencimento < hoje
            )
        ).scalar() or 0
        
        # ========================================
        # 3. CONTAS A PAGAR
        # ========================================
        contas_pagar_total = db.query(
            func.sum(ContaPagar.valor_final - ContaPagar.valor_pago)
        ).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status.in_(['pendente', 'parcial', 'vencida'])
            )
        ).scalar() or 0
        
        # Contas vencidas a pagar
        contas_pagar_vencidas = db.query(
            func.sum(ContaPagar.valor_final - ContaPagar.valor_pago)
        ).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status.in_(['pendente', 'parcial', 'vencida']),
                ContaPagar.data_vencimento < hoje
            )
        ).scalar() or 0
        
        # ========================================
        # 4. VENDAS DO PERÍODO
        # ========================================
        vendas_periodo = db.query(
            func.count(Venda.id).label('quantidade'),
            func.sum(Venda.total).label('valor_total')
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo
            )
        ).first()
        
        total_vendas_periodo = vendas_periodo.valor_total or 0
        quantidade_vendas_periodo = vendas_periodo.quantidade or 0
        
        # Vendas finalizadas
        vendas_finalizadas = db.query(
            func.sum(Venda.total)
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo,
                Venda.status == 'finalizada'
            )
        ).scalar() or 0
        
        # ========================================
        # 5. ENTRADAS E SAÍDAS DO PERÍODO (baseado em vendas e contas)
        # ========================================
        entradas_periodo = db.query(
            func.sum(Venda.total)
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo,
                Venda.status == 'finalizada'
            )
        ).scalar() or 0
        
        saidas_periodo = db.query(
            func.sum(ContaPagar.valor_pago)
        ).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.data_pagamento >= inicio_periodo
            )
        ).scalar() or 0
        
        # ========================================
        # 6. LUCRO DO PERÍODO
        # ========================================
        lucro_periodo = entradas_periodo - saidas_periodo
        
        # ========================================
        # 7. TICKET MÉDIO
        # ========================================
        ticket_medio = (total_vendas_periodo / quantidade_vendas_periodo) if quantidade_vendas_periodo > 0 else 0
        
        # ========================================
        # RETORNO
        # ========================================
        return {
            "saldo_atual": round(saldo_atual, 2),
            "contas_receber": {
                "total": round(contas_receber_total, 2),
                "vencidas": round(contas_receber_vencidas, 2)
            },
            "contas_pagar": {
                "total": round(contas_pagar_total, 2),
                "vencidas": round(contas_pagar_vencidas, 2)
            },
            "vendas_periodo": {
                "quantidade": quantidade_vendas_periodo,
                "valor_total": round(total_vendas_periodo, 2),
                "finalizadas": round(vendas_finalizadas, 2),
                "ticket_medio": round(ticket_medio, 2)
            },
            "fluxo_periodo": {
                "entradas": round(entradas_periodo, 2),
                "saidas": round(saidas_periodo, 2),
                "lucro": round(lucro_periodo, 2)
            },
            "periodo_dias": periodo_dias
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter resumo do dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/entradas-saidas")
async def obter_entradas_saidas_por_dia(
    periodo_dias: int = 30,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna entradas e saídas agrupadas por dia para gráfico
    """
    current_user, tenant_id = user_and_tenant
    try:
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)
        
        # Buscar vendas por dia
        vendas = db.query(
            func.date(Venda.data_venda).label('data'),
            func.sum(Venda.total).label('total')
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo,
                Venda.status == 'finalizada'
            )
        ).group_by(
            func.date(Venda.data_venda)
        ).all()
        
        # Buscar pagamentos por dia
        pagamentos = db.query(
            func.date(ContaPagar.data_pagamento).label('data'),
            func.sum(ContaPagar.valor_pago).label('total')
        ).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.data_pagamento >= inicio_periodo
            )
        ).group_by(
            func.date(ContaPagar.data_pagamento)
        ).all()
        
        # Organizar por data
        dados_por_dia = {}
        
        # Inicializar todos os dias com zero
        for i in range(periodo_dias + 1):
            data = (inicio_periodo + timedelta(days=i)).strftime('%Y-%m-%d')
            dados_por_dia[data] = {
                'data': data,
                'entradas': 0,
                'saidas': 0
            }
        
        # Preencher com vendas
        for venda in vendas:
            data_obj = venda[0] if isinstance(venda, tuple) else venda.data
            data_str = data_obj.strftime('%Y-%m-%d') if hasattr(data_obj, 'strftime') else str(data_obj)
            if data_str in dados_por_dia:
                dados_por_dia[data_str]['entradas'] = float(venda.total or 0)
        
        # Preencher com pagamentos
        for pagamento in pagamentos:
            data_obj = pagamento[0] if isinstance(pagamento, tuple) else pagamento.data
            data_str = data_obj.strftime('%Y-%m-%d') if hasattr(data_obj, 'strftime') else str(data_obj)
            if data_str in dados_por_dia:
                dados_por_dia[data_str]['saidas'] = float(pagamento.total or 0)
        
        # Converter para lista ordenada
        resultado = sorted(dados_por_dia.values(), key=lambda x: x['data'])
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao obter entradas/saídas por dia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/vendas-por-dia")
async def obter_vendas_por_dia(
    periodo_dias: int = 30,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna vendas agrupadas por dia para gráfico
    """
    current_user, tenant_id = user_and_tenant
    try:
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)
        
        # Buscar vendas do período
        vendas = db.query(
            func.date(Venda.data_venda).label('data'),
            func.count(Venda.id).label('quantidade'),
            func.sum(Venda.total).label('valor_total')
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo
            )
        ).group_by(
            func.date(Venda.data_venda)
        ).all()
        
        # Organizar por data
        dados_por_dia = {}
        
        # Inicializar todos os dias com zero
        for i in range(periodo_dias + 1):
            data = (inicio_periodo + timedelta(days=i)).strftime('%Y-%m-%d')
            dados_por_dia[data] = {
                'data': data,
                'quantidade': 0,
                'valor_total': 0
            }
        
        # Preencher com dados reais
        for venda in vendas:
            # venda é um resultado de query com labels, não um objeto Venda
            data_obj = venda[0] if isinstance(venda, tuple) else venda.data
            data_str = data_obj.strftime('%Y-%m-%d') if hasattr(data_obj, 'strftime') else str(data_obj)
            if data_str in dados_por_dia:
                dados_por_dia[data_str]['quantidade'] = int(venda.quantidade) if venda.quantidade else 0
                dados_por_dia[data_str]['valor_total'] = float(venda.valor_total or 0)
        
        # Converter para lista ordenada
        resultado = sorted(dados_por_dia.values(), key=lambda x: x['data'])
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao obter vendas por dia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/contas-vencidas")
async def obter_contas_vencidas(
    limite: int = 10,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna contas a receber e pagar vencidas (não pagas)
    """
    current_user, tenant_id = user_and_tenant
    
    try:
        hoje = datetime.now().date()
        
        # Contas a receber vencidas
        contas_receber = db.query(ContaReceber).filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status.in_(['pendente', 'parcial', 'vencido']),
                ContaReceber.data_vencimento < hoje
            )
        ).order_by(ContaReceber.data_vencimento.asc()).limit(limite).all()
        
        # Contas a pagar vencidas
        contas_pagar = db.query(ContaPagar).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status.in_(['pendente', 'parcial', 'vencido']),
                ContaPagar.data_vencimento < hoje
            )
        ).order_by(ContaPagar.data_vencimento.asc()).limit(limite).all()
        
        return {
            "contas_receber": [
                {
                    "id": c.id,
                    "descricao": c.descricao,
                    "cliente": c.cliente.nome if c.cliente else None,
                    "valor_total": float(c.valor_final),
                    "valor_pago": float(c.valor_recebido),
                    "saldo": float(c.valor_final - c.valor_recebido),
                    "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
                    "dias_vencido": (hoje - c.data_vencimento).days if c.data_vencimento else 0,
                    "status": c.status
                }
                for c in contas_receber
            ],
            "contas_pagar": [
                {
                    "id": c.id,
                    "descricao": c.descricao,
                    "fornecedor": c.fornecedor.nome if c.fornecedor else None,
                    "valor_total": float(c.valor_final),
                    "valor_pago": float(c.valor_pago),
                    "saldo": float(c.valor_final - c.valor_pago),
                    "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
                    "dias_vencido": (hoje - c.data_vencimento).days if c.data_vencimento else 0,
                    "status": c.status
                }
                for c in contas_pagar
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter contas vencidas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/top-produtos")
async def obter_top_produtos(
    periodo_dias: int = 30,
    limite: int = 10,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna os produtos mais vendidos no período
    """
    current_user, tenant_id = user_and_tenant
    try:
        from .vendas_models import VendaItem
        from .produtos_models import Produto
        
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)
        
        # Buscar produtos mais vendidos
        top_produtos = db.query(
            Produto.nome,
            func.sum(VendaItem.quantidade).label('total_vendido'),
            func.sum(VendaItem.subtotal).label('receita_total')
        ).join(
            VendaItem, Produto.id == VendaItem.produto_id
        ).join(
            Venda, VendaItem.venda_id == Venda.id
        ).filter(
            and_(
                Venda.tenant_id == tenant_id,
                Produto.tenant_id == tenant_id,
                Venda.data_venda >= inicio_periodo
            )
        ).group_by(
            Produto.id, Produto.nome
        ).order_by(
            func.sum(VendaItem.quantidade).desc()
        ).limit(limite).all()
        
        return [
            {
                "nome": p.nome,
                "quantidade_vendida": int(p.total_vendido),
                "receita_total": float(p.receita_total or 0)
            }
            for p in top_produtos
        ]
        
    except Exception as e:
        logger.error(f"Erro ao obter top produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
