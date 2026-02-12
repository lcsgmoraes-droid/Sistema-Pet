# ============================================================================
# SPRINT 7: Analytics Simplificado
# Versão compatível com os campos reais dos models
# ============================================================================

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from app.whatsapp.models import (
    WhatsAppSession,
    WhatsAppMessage,
    TenantWhatsAppConfig
)
from app.whatsapp.models_handoff import WhatsAppHandoff


class WhatsAppAnalyticsService:
    """Serviço de analytics para WhatsApp"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    def get_dashboard_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Retorna métricas principais do dashboard"""
        
        # Período padrão: últimos 30 dias
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Total de conversas
        total_sessions = self.db.query(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppSession.started_at >= start_date,
                WhatsAppSession.started_at <= end_date
            )
        ).count()
        
        # Total de mensagens
        total_messages = self.db.query(WhatsAppMessage).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppMessage.created_at >= start_date,
                WhatsAppMessage.created_at <= end_date
            )
        ).count()
        
        # Conversas com handoff
        total_handoffs = self.db.query(WhatsAppHandoff).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppHandoff.created_at >= start_date,
                WhatsAppHandoff.created_at <= end_date
            )
        ).count()
        
        # Taxa de resolução automática
        auto_resolution_rate = 0.0
        if total_sessions > 0:
            auto_resolution_rate = ((total_sessions - total_handoffs) / total_sessions) * 100
        
        # Intenções mais comuns
        top_intents = self.db.query(
            WhatsAppMessage.intent_detected,
            func.count(WhatsAppMessage.id).label('count')
        ).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppMessage.created_at >= start_date,
                WhatsAppMessage.created_at <= end_date,
                WhatsAppMessage.intent_detected.isnot(None)
            )
        ).group_by(
            WhatsAppMessage.intent_detected
        ).order_by(
            func.count(WhatsAppMessage.id).desc()
        ).limit(10).all()
        
        # Horários de pico
        peak_hours = self.db.query(
            func.extract('hour', WhatsAppMessage.created_at).label('hour'),
            func.count(WhatsAppMessage.id).label('count')
        ).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppMessage.created_at >= start_date,
                WhatsAppMessage.created_at <= end_date
            )
        ).group_by(
            func.extract('hour', WhatsAppMessage.created_at)
        ).order_by(
            func.count(WhatsAppMessage.id).desc()
        ).limit(5).all()
        
        # Tokens utilizados (onde disponível)
        total_tokens = self.db.query(
            func.sum(WhatsAppMessage.tokens_input + WhatsAppMessage.tokens_output)
        ).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppMessage.created_at >= start_date,
                WhatsAppMessage.created_at <= end_date,
                WhatsAppMessage.tokens_input.isnot(None)
            )
        ).scalar() or 0
        
        # Custo estimado (GPT-4o-mini: $0.15/1M input, $0.60/1M output)
        estimated_cost = (total_tokens * 0.375) / 1_000_000  # Média entre input e output
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "conversations": {
                "total": total_sessions,
                "with_handoff": total_handoffs,
                "auto_resolved": total_sessions - total_handoffs,
                "auto_resolution_rate": round(auto_resolution_rate, 2)
            },
            "messages": {
                "total": total_messages,
                "avg_per_conversation": round(total_messages / total_sessions, 2) if total_sessions > 0 else 0
            },
            "response_time": {
                "avg_seconds": 0,  # TODO: Calcular quando tiver dados
                "avg_minutes": 0
            },
            "costs": {
                "total": round(estimated_cost, 2),
                "per_conversation": round(estimated_cost / total_sessions, 4) if total_sessions > 0 else 0,
                "currency": "USD",
                "total_tokens": int(total_tokens)
            },
            "intents": [{"intent": i.intent_detected, "count": i.count} for i in top_intents],
            "peak_hours": [{"hour": int(h.hour), "count": h.count} for h in peak_hours],
            "sentiment": {
                "average": 0,  # TODO: Calcular quando tiver dados
                "label": "neutral"
            }
        }
    
    def get_conversation_trends(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "day"
    ) -> Dict:
        """Retorna tendências de conversas ao longo do tempo"""
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Conversas por dia
        daily_conversations = self.db.query(
            func.date(WhatsAppSession.started_at).label('date'),
            func.count(WhatsAppSession.id).label('count')
        ).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppSession.started_at >= start_date,
                WhatsAppSession.started_at <= end_date
            )
        ).group_by(
            func.date(WhatsAppSession.started_at)
        ).order_by(
            func.date(WhatsAppSession.started_at)
        ).all()
        
        # Mensagens por dia
        daily_messages = self.db.query(
            func.date(WhatsAppMessage.created_at).label('date'),
            func.count(WhatsAppMessage.id).label('count')
        ).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppMessage.created_at >= start_date,
                WhatsAppMessage.created_at <= end_date
            )
        ).group_by(
            func.date(WhatsAppMessage.created_at)
        ).order_by(
            func.date(WhatsAppMessage.created_at)
        ).all()
        
        return {
            "period_days": (end_date - start_date).days,
            "daily_conversations": [{"date": str(d.date), "count": d.count} for d in daily_conversations],
            "daily_messages": [{"date": str(d.date), "count": d.count} for d in daily_messages]
        }
    
    def get_handoff_analysis(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Análise detalhada de handoffs"""
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Total de handoffs
        total_handoffs = self.db.query(WhatsAppHandoff).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppHandoff.created_at >= start_date,
                WhatsAppHandoff.created_at <= end_date
            )
        ).count()
        
        # Handoffs por motivo
        handoffs_by_reason = self.db.query(
            WhatsAppHandoff.reason,
            func.count(WhatsAppHandoff.id).label('count')
        ).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppHandoff.created_at >= start_date,
                WhatsAppHandoff.created_at <= end_date
            )
        ).group_by(
            WhatsAppHandoff.reason
        ).all()
        
        # Handoffs por prioridade
        handoffs_by_priority = self.db.query(
            WhatsAppHandoff.priority,
            func.count(WhatsAppHandoff.id).label('count')
        ).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppHandoff.created_at >= start_date,
                WhatsAppHandoff.created_at <= end_date
            )
        ).group_by(
            WhatsAppHandoff.priority
        ).all()
        
        return {
            "total_handoffs": total_handoffs,
            "by_reason": {reason if reason else "unknown": count for reason, count in handoffs_by_reason},
            "by_priority": {priority: count for priority, count in handoffs_by_priority},
            "avg_resolution_time_seconds": 0,  # TODO
            "avg_resolution_time_minutes": 0
        }
    
    def get_cost_analysis(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Análise detalhada de custos"""
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Custo total por tipo de mensagem
        costs = self.db.query(
            WhatsAppMessage.tipo,
            func.sum(WhatsAppMessage.tokens_input + WhatsAppMessage.tokens_output).label('total_tokens'),
            func.count(WhatsAppMessage.id).label('message_count')
        ).join(WhatsAppSession).filter(
            and_(
                WhatsAppSession.tenant_id == self.tenant_id,
                WhatsAppMessage.created_at >= start_date,
                WhatsAppMessage.created_at <= end_date,
                WhatsAppMessage.tokens_input.isnot(None)
            )
        ).group_by(
            WhatsAppMessage.tipo
        ).all()
        
        total_tokens = sum(c.total_tokens or 0 for c in costs)
        total_cost = (total_tokens * 0.375) / 1_000_000  # Estimativa
        
        return {
            "total_cost": round(total_cost, 2),
            "total_tokens": int(total_tokens),
            "by_direction": [
                {
                    "direction": c.tipo,
                    "total_tokens": c.total_tokens or 0,
                    "message_count": c.message_count,
                    "estimated_cost": round(((c.total_tokens or 0) * 0.375) / 1_000_000, 4)
                }
                for c in costs
            ],
            "currency": "USD"
        }
    
    def get_agent_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Retorna performance de cada atendente humano
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Performance por agente
        from app.whatsapp.models_handoff import WhatsAppAgent
        
        agents = self.db.query(WhatsAppAgent).filter(
            WhatsAppAgent.tenant_id == self.tenant_id,
            WhatsAppAgent.is_active == True
        ).all()
        
        performance_list = []
        
        for agent in agents:
            # Handoffs atribuídos
            total_handoffs = self.db.query(WhatsAppHandoff).filter(
                and_(
                    WhatsAppHandoff.agent_id == agent.id,
                    WhatsAppHandoff.created_at >= start_date,
                    WhatsAppHandoff.created_at <= end_date
                )
            ).count()
            
            # Handoffs resolvidos
            resolved_handoffs = self.db.query(WhatsAppHandoff).filter(
                and_(
                    WhatsAppHandoff.agent_id == agent.id,
                    WhatsAppHandoff.status == 'resolved',
                    WhatsAppHandoff.created_at >= start_date,
                    WhatsAppHandoff.created_at <= end_date
                )
            ).count()
            
            # Taxa de resolução
            resolution_rate = (resolved_handoffs / total_handoffs * 100) if total_handoffs > 0 else 0
            
            # Tempo médio de resolução (em minutos)
            avg_time = self.db.query(
                func.avg(
                    func.extract('epoch', WhatsAppHandoff.resolved_at - WhatsAppHandoff.created_at) / 60
                )
            ).filter(
                and_(
                    WhatsAppHandoff.agent_id == agent.id,
                    WhatsAppHandoff.resolved_at.isnot(None),
                    WhatsAppHandoff.created_at >= start_date,
                    WhatsAppHandoff.created_at <= end_date
                )
            ).scalar() or 0
            
            performance_list.append({
                "agent_id": agent.id,
                "user_id": agent.user_id,
                "is_online": agent.is_online,
                "total_handoffs": total_handoffs,
                "resolved_handoffs": resolved_handoffs,
                "pending_handoffs": total_handoffs - resolved_handoffs,
                "resolution_rate": round(resolution_rate, 2),
                "avg_resolution_time_minutes": round(avg_time, 2)
            })
        
        return performance_list
    
    def get_nps_score(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Calcula Net Promoter Score (NPS)
        
        Nota: Requer implementação de sistema de avaliação
        Por enquanto, retorna estrutura básica
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # TODO: Implementar quando houver sistema de avaliação
        # Por enquanto, retorna estrutura base
        
        return {
            "nps_score": 0,
            "total_responses": 0,
            "promoters": 0,
            "neutrals": 0,
            "detractors": 0,
            "promoters_percentage": 0,
            "detractors_percentage": 0,
            "note": "Sistema de avaliação será implementado em breve"
        }
