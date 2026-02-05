"""
Serviço de Métricas de Oportunidades - FASE 2

Módulo de consultas read-only para análise de oportunidades.
Fornece dados para relatórios, dashboards e análise de performance futura.

REGRA: Apenas SELECT (zero mutations).
Todas as queries filtram por tenant_id automaticamente.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from uuid import UUID

from sqlalchemy import func, and_, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.opportunity_events_models import OpportunityEvent, OpportunityEventTypeEnum
from app.opportunities_models import Opportunity


def count_events_by_type(
    tenant_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, int]:
    """
    Conta eventos de oportunidade por tipo no período.
    
    Responde: Quantas vezes cada ação foi disparada (Adicionar, Alternativa, Ignorar)?
    
    Uso futuro: Dashboard com distribuição de ações, tendências de comportamento.
    
    Args:
        tenant_id: UUID do tenant
        start_date: Data inicial (padrão: últimos 30 dias)
        end_date: Data final (padrão: hoje)
    
    Returns:
        Dict com contagem por tipo:
        {
            "convertida": 150,
            "refinada": 45,
            "rejeitada": 23
        }
    """
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()
    
    try:
        session = SessionLocal()
        
        query = (
            select(
                OpportunityEvent.event_type,
                func.count(OpportunityEvent.id).label('count')
            )
            .where(
                and_(
                    OpportunityEvent.tenant_id == tenant_id,
                    OpportunityEvent.created_at >= start_date,
                    OpportunityEvent.created_at <= end_date
                )
            )
            .group_by(OpportunityEvent.event_type)
        )
        
        results = session.execute(query).fetchall()
        session.close()
        
        return {
            row[0].value: row[1]
            for row in results
        }
    
    except Exception as e:
        logger.info(f"Erro ao contar eventos por tipo: {str(e)}")
        return {}


def conversion_rate_by_type(
    tenant_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, float]:
    """
    Calcula taxa de conversão por tipo de oportunidade.
    
    Responde: Qual é a taxa de sucesso para cada tipo de oportunidade?
    Taxa = (convertidas / total) * 100
    
    Uso futuro: Identificar qual tipo de sugestão tem maior aceitação.
    Treinar IA com foco em tipos com maior taxa de conversão.
    
    Args:
        tenant_id: UUID do tenant
        start_date: Data inicial
        end_date: Data final
    
    Returns:
        Dict com taxa (0-100) por tipo:
        {
            "cross_sell_rate": 65.5,
            "up_sell_rate": 42.3,
            "recorrencia_rate": 78.9
        }
    """
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()
    
    try:
        session = SessionLocal()
        
        # Total de eventos convertidas
        total_convertidas = session.query(
            func.count(OpportunityEvent.id)
        ).filter(
            and_(
                OpportunityEvent.tenant_id == tenant_id,
                OpportunityEvent.event_type == OpportunityEventTypeEnum.CONVERTIDA,
                OpportunityEvent.created_at >= start_date,
                OpportunityEvent.created_at <= end_date
            )
        ).scalar() or 0
        
        # Total de todos os eventos
        total_eventos = session.query(
            func.count(OpportunityEvent.id)
        ).filter(
            and_(
                OpportunityEvent.tenant_id == tenant_id,
                OpportunityEvent.created_at >= start_date,
                OpportunityEvent.created_at <= end_date
            )
        ).scalar() or 0
        
        session.close()
        
        if total_eventos == 0:
            return {"overall_conversion_rate": 0.0}
        
        rate = (total_convertidas / total_eventos) * 100
        
        return {
            "overall_conversion_rate": round(rate, 2),
            "total_events": total_eventos,
            "total_converted": total_convertidas
        }
    
    except Exception as e:
        logger.info(f"Erro ao calcular taxa de conversão: {str(e)}")
        return {}


def top_products_converted(
    tenant_id: UUID,
    limit: int = 10
) -> List[Dict[str, any]]:
    """
    Produtos mais frequentemente CONVERTIDOS (adicionados ao carrinho).
    
    Responde: Quais produtos são mais aceitos quando sugeridos?
    
    Uso futuro: Identificar produtos "vencedores" para priorizar em sugestões.
    Treinar IA para aumentar frequência de sugestão dos produtos com alta conversão.
    
    Args:
        tenant_id: UUID do tenant
        limit: Número máximo de produtos (padrão: 10)
    
    Returns:
        Lista de dicts:
        [
            {
                "produto_id": 123,
                "conversoes": 45,
                "tipo": "cross_sell"
            },
            ...
        ]
    """
    try:
        session = SessionLocal()
        
        query = (
            select(
                OpportunityEvent.metadata['produto_sugerido_id'].astext.label('produto_id'),
                func.count(OpportunityEvent.id).label('count')
            )
            .where(
                and_(
                    OpportunityEvent.tenant_id == tenant_id,
                    OpportunityEvent.event_type == OpportunityEventTypeEnum.CONVERTIDA
                )
            )
            .group_by(OpportunityEvent.metadata['produto_sugerido_id'].astext)
            .order_by(func.count(OpportunityEvent.id).desc())
            .limit(limit)
        )
        
        results = session.execute(query).fetchall()
        session.close()
        
        return [
            {
                "produto_id": row[0],
                "conversoes": row[1]
            }
            for row in results
        ]
    
    except Exception as e:
        logger.info(f"Erro ao buscar produtos convertidos: {str(e)}")
        return []


def top_products_ignored(
    tenant_id: UUID,
    limit: int = 10
) -> List[Dict[str, any]]:
    """
    Produtos mais frequentemente IGNORADOS (rejeitados sem alternativa).
    
    Responde: Quais produtos são mais rejeitados? Não são bons candidatos?
    
    Uso futuro: Remover esses produtos de sugestões futuras.
    Ajustar critérios de seleção para reduzir rejeição.
    
    Args:
        tenant_id: UUID do tenant
        limit: Número máximo de produtos (padrão: 10)
    
    Returns:
        Lista de dicts:
        [
            {
                "produto_id": 456,
                "rejeicoes": 12
            },
            ...
        ]
    """
    try:
        session = SessionLocal()
        
        query = (
            select(
                OpportunityEvent.metadata['produto_sugerido_id'].astext.label('produto_id'),
                func.count(OpportunityEvent.id).label('count')
            )
            .where(
                and_(
                    OpportunityEvent.tenant_id == tenant_id,
                    OpportunityEvent.event_type == OpportunityEventTypeEnum.REJEITADA
                )
            )
            .group_by(OpportunityEvent.metadata['produto_sugerido_id'].astext)
            .order_by(func.count(OpportunityEvent.id).desc())
            .limit(limit)
        )
        
        results = session.execute(query).fetchall()
        session.close()
        
        return [
            {
                "produto_id": row[0],
                "rejeicoes": row[1]
            }
            for row in results
        ]
    
    except Exception as e:
        logger.info(f"Erro ao buscar produtos ignorados: {str(e)}")
        return []


def operator_event_summary(
    tenant_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, any]]:
    """
    Resumo de ações de cada operador (caixa) no período.
    
    Responde: Qual operador tem melhor taxa de conversão?
    Como diferentes operadores usam o sistema de oportunidades?
    
    Uso futuro: Identificar operadores "super" para treinamento.
    Comparar performance e treinar os outros no melhor método.
    
    Args:
        tenant_id: UUID do tenant
        start_date: Data inicial
        end_date: Data final
    
    Returns:
        Lista de dicts com resumo por operador:
        [
            {
                "user_id": "uuid-1",
                "total_eventos": 50,
                "convertidas": 30,
                "refinadas": 15,
                "rejeitadas": 5,
                "taxa_conversao": 60.0
            },
            ...
        ]
    """
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()
    
    try:
        session = SessionLocal()
        
        # Aggregate por operador
        query = (
            select(
                OpportunityEvent.user_id,
                func.count(OpportunityEvent.id).label('total'),
                func.sum(
                    func.cast(
                        OpportunityEvent.event_type == OpportunityEventTypeEnum.CONVERTIDA,
                        sqlalchemy.Integer
                    )
                ).label('convertidas'),
                func.sum(
                    func.cast(
                        OpportunityEvent.event_type == OpportunityEventTypeEnum.REFINADA,
                        sqlalchemy.Integer
                    )
                ).label('refinadas'),
                func.sum(
                    func.cast(
                        OpportunityEvent.event_type == OpportunityEventTypeEnum.REJEITADA,
                        sqlalchemy.Integer
                    )
                ).label('rejeitadas')
            )
            .where(
                and_(
                    OpportunityEvent.tenant_id == tenant_id,
                    OpportunityEvent.created_at >= start_date,
                    OpportunityEvent.created_at <= end_date
                )
            )
            .group_by(OpportunityEvent.user_id)
            .order_by(func.count(OpportunityEvent.id).desc())
        )
        
        results = session.execute(query).fetchall()
        session.close()
        
        summary = []
        for row in results:
            total = row.total or 0
            convertidas = row.convertidas or 0
            
            taxa_conversao = (convertidas / total * 100) if total > 0 else 0
            
            summary.append({
                "user_id": str(row.user_id),
                "total_eventos": total,
                "convertidas": convertidas,
                "refinadas": row.refinadas or 0,
                "rejeitadas": row.rejeitadas or 0,
                "taxa_conversao": round(taxa_conversao, 2)
            })
        
        return summary
    
    except Exception as e:
        logger.info(f"Erro ao gerar resumo de operadores: {str(e)}")
        return []


def get_metrics_dashboard_summary(
    tenant_id: UUID,
    days: int = 30
) -> Dict[str, any]:
    """
    Resumo consolidado para dashboard de métricas.
    
    Responde: Qual é o estado geral das oportunidades neste período?
    
    Uso futuro: Exibir na página de métricas/analytics.
    Mostrar KPIs principais de performance.
    
    Args:
        tenant_id: UUID do tenant
        days: Número de dias a retroagir (padrão: 30)
    
    Returns:
        Dict com resumo consolidado:
        {
            "periodo": "últimos 30 dias",
            "total_eventos": 218,
            "taxas": {
                "conversao": 65.5,
                "refinacao": 20.0,
                "rejeicao": 14.5
            },
            "produtos_top": [...],
            "operadores_top": [...]
        }
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        events_by_type = count_events_by_type(tenant_id, start_date, end_date)
        conversion_data = conversion_rate_by_type(tenant_id, start_date, end_date)
        top_produtos = top_products_converted(tenant_id, limit=5)
        top_operadores = operator_event_summary(tenant_id, start_date, end_date)[:5]
        
        total_events = conversion_data.get('total_events', 0)
        
        if total_events > 0:
            taxas = {
                "conversao": round(
                    (events_by_type.get('oportunidade_convertida', 0) / total_events) * 100, 2
                ),
                "refinacao": round(
                    (events_by_type.get('oportunidade_refinada', 0) / total_events) * 100, 2
                ),
                "rejeicao": round(
                    (events_by_type.get('oportunidade_rejeitada', 0) / total_events) * 100, 2
                )
            }
        else:
            taxas = {"conversao": 0.0, "refinacao": 0.0, "rejeicao": 0.0}
        
        return {
            "tenant_id": str(tenant_id),
            "periodo": f"últimos {days} dias",
            "data_inicio": start_date.isoformat(),
            "data_fim": end_date.isoformat(),
            "total_eventos": total_events,
            "eventos_por_tipo": events_by_type,
            "taxas": taxas,
            "produtos_top": top_produtos,
            "operadores_top": top_operadores
        }
    
    except Exception as e:
        logger.info(f"Erro ao gerar resumo do dashboard: {str(e)}")
        return {}


# Import no final para evitar circular imports
import sqlalchemy
from app.utils.logger import logger
