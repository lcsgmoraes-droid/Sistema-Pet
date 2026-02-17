# ============================================================================
# SPRINT 7: Analytics & Optimization
# Serviço de análises avançadas para WhatsApp + IA
# ============================================================================

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_, extract
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
        """
        Retorna métricas completas para dashboard
        
        Métricas incluídas:
        - Total de conversas
        - Taxa de resolução automática
        - Tempo médio de resposta
        - Custo por conversa
        - Intenções mais comuns
        - Horários de pico
        - Taxa de conversão
        """
        
        # Período padrão: últimos 30 dias
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Base query com filtro de tenant e período
        session_query = self.db.query(WhatsAppSession).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppSession.started_at.between(start_date, end_date)
        )
        
        message_query = self.db.query(WhatsAppMessage).join(
            WhatsAppSession,
            WhatsAppMessage.session_id == WhatsAppSession.id
        ).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppMessage.created_at.between(start_date, end_date)
        )
        
        handoff_query = self.db.query(WhatsAppHandoff).join(
            WhatsAppSession,
            WhatsAppHandoff.session_id == WhatsAppSession.id
        ).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppHandoff.created_at.between(start_date, end_date)
        )
        
        # 1. Total de conversas
        total_sessions = session_query.count()
        
        # 2. Taxa de resolução automática
        total_handoffs = handoff_query.count()
        auto_resolution_rate = (
            ((total_sessions - total_handoffs) / total_sessions * 100)
            if total_sessions > 0 else 0
        )
        
        # 3. Tempo médio de resposta (em segundos)
        avg_response_time_query = self.db.query(
            func.avg(
                func.extract('epoch', WhatsAppMessage.created_at) -
                func.lag(func.extract('epoch', WhatsAppMessage.created_at))
                .over(partition_by=WhatsAppMessage.session_id, order_by=WhatsAppMessage.created_at)
            ).label('avg_time')
        ).join(
            WhatsAppSession,
            WhatsAppMessage.session_id == WhatsAppSession.id
        ).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppMessage.direction == 'outgoing',
            WhatsAppMessage.created_at.between(start_date, end_date)
        )
        
        avg_response_time = avg_response_time_query.scalar() or 0
        
        # 4. Custo por conversa
        total_cost_query = session_query.with_entities(
            func.sum(WhatsAppSession.total_cost)
        )
        total_cost = total_cost_query.scalar() or 0.0
        cost_per_conversation = (
            (total_cost / total_sessions)
            if total_sessions > 0 else 0
        )
        
        # 5. Total de mensagens
        total_messages = message_query.count()
        incoming_messages = message_query.filter(
            WhatsAppMessage.direction == 'incoming'
        ).count()
        outgoing_messages = message_query.filter(
            WhatsAppMessage.direction == 'outgoing'
        ).count()
        
        # 6. Intenções mais comuns
        intent_stats = self.db.query(
            WhatsAppMessage.intent,
            func.count(WhatsAppMessage.id).label('count')
        ).join(
            WhatsAppSession,
            WhatsAppMessage.session_id == WhatsAppSession.id
        ).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppMessage.intent.isnot(None),
            WhatsAppMessage.created_at.between(start_date, end_date)
        ).group_by(
            WhatsAppMessage.intent
        ).order_by(
            func.count(WhatsAppMessage.id).desc()
        ).limit(10).all()
        
        top_intents = [
            {"intent": row.intent, "count": row.count}
            for row in intent_stats
        ]
        
        # 7. Horários de pico (por hora do dia)
        peak_hours_query = self.db.query(
            extract('hour', WhatsAppMessage.created_at).label('hour'),
            func.count(WhatsAppMessage.id).label('count')
        ).join(
            WhatsAppSession,
            WhatsAppMessage.session_id == WhatsAppSession.id
        ).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppMessage.created_at.between(start_date, end_date)
        ).group_by(
            extract('hour', WhatsAppMessage.created_at)
        ).order_by(
            extract('hour', WhatsAppMessage.created_at)
        ).all()
        
        peak_hours = [
            {"hour": int(row.hour), "count": row.count}
            for row in peak_hours_query
        ]
        
        # 8. Sentiment analysis distribution
        sentiment_stats = self.db.query(
            WhatsAppMessage.sentiment,
            func.count(WhatsAppMessage.id).label('count')
        ).join(
            WhatsAppSession,
            WhatsAppMessage.session_id == WhatsAppSession.id
        ).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppMessage.sentiment.isnot(None),
            WhatsAppMessage.created_at.between(start_date, end_date)
        ).group_by(
            WhatsAppMessage.sentiment
        ).all()
        
        sentiment_distribution = {
            "positive": 0,
            "neutral": 0,
            "negative": 0
        }
        
        for row in sentiment_stats:
            if row.sentiment > 0.3:
                sentiment_distribution["positive"] += row.count
            elif row.sentiment < -0.3:
                sentiment_distribution["negative"] += row.count
            else:
                sentiment_distribution["neutral"] += row.count
        
        # 9. Handoff statistics
        handoff_stats = {
            "total": total_handoffs,
            "resolved": handoff_query.filter(
                WhatsAppHandoff.status == 'resolved'
            ).count(),
            "pending": handoff_query.filter(
                WhatsAppHandoff.status == 'pending'
            ).count(),
            "in_progress": handoff_query.filter(
                WhatsAppHandoff.status == 'in_progress'
            ).count()
        }
        
        # 10. Tools usage
        tools_usage_query = self.db.query(
            WhatsAppMessage.tools_used
        ).join(
            WhatsAppSession,
            WhatsAppMessage.session_id == WhatsAppSession.id
        ).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppMessage.tools_used.isnot(None),
            WhatsAppMessage.created_at.between(start_date, end_date)
        ).all()
        
        tools_counter: Dict[str, int] = {}
        for row in tools_usage_query:
            if row.tools_used:
                for tool in row.tools_used:
                    tools_counter[tool] = tools_counter.get(tool, 0) + 1
        
        top_tools = [
            {"tool": tool, "count": count}
            for tool, count in sorted(
                tools_counter.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        ]
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "overview": {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "incoming_messages": incoming_messages,
                "outgoing_messages": outgoing_messages,
                "auto_resolution_rate": round(auto_resolution_rate, 2),
                "avg_response_time_seconds": round(avg_response_time, 2),
                "total_cost_usd": round(total_cost, 2),
                "cost_per_conversation_usd": round(cost_per_conversation, 4)
            },
            "intents": top_intents,
            "peak_hours": peak_hours,
            "sentiment": sentiment_distribution,
            "handoffs": handoff_stats,
            "tools": top_tools
        }
    
    def get_conversation_trends(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = 'day'  # 'hour', 'day', 'week', 'month'
    ) -> List[Dict[str, Any]]:
        """
        Retorna tendências de conversas ao longo do tempo
        """
        
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Determinar o agrupamento temporal
        if interval == 'hour':
            time_group = func.date_trunc('hour', WhatsAppSession.started_at)
        elif interval == 'day':
            time_group = func.date_trunc('day', WhatsAppSession.started_at)
        elif interval == 'week':
            time_group = func.date_trunc('week', WhatsAppSession.started_at)
        elif interval == 'month':
            time_group = func.date_trunc('month', WhatsAppSession.started_at)
        else:
            time_group = func.date_trunc('day', WhatsAppSession.started_at)
        
        trends = self.db.query(
            time_group.label('period'),
            func.count(WhatsAppSession.id).label('sessions'),
            func.sum(WhatsAppSession.total_cost).label('cost')
        ).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppSession.started_at.between(start_date, end_date)
        ).group_by(
            time_group
        ).order_by(
            time_group
        ).all()
        
        return [
            {
                "period": row.period.isoformat() if row.period else None,
                "sessions": row.sessions,
                "cost_usd": round(float(row.cost or 0), 2)
            }
            for row in trends
        ]
    
    def get_agent_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna performance de cada atendente humano
        """
        
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        from app.whatsapp.models import WhatsAppAgent
        
        # Query para performance de cada agente
        performance = self.db.query(
            WhatsAppAgent.id,
            WhatsAppAgent.name,
            WhatsAppAgent.email,
            func.count(WhatsAppHandoff.id).label('total_handoffs'),
            func.count(
                func.nullif(WhatsAppHandoff.status == 'resolved', False)
            ).label('resolved'),
            func.avg(
                func.extract(
                    'epoch',
                    WhatsAppHandoff.resolved_at - WhatsAppHandoff.assigned_at
                )
            ).label('avg_resolution_time')
        ).outerjoin(
            WhatsAppHandoff,
            and_(
                WhatsAppHandoff.assigned_agent_id == WhatsAppAgent.id,
                WhatsAppHandoff.created_at.between(start_date, end_date)
            )
        ).filter(
            WhatsAppAgent.tenant_id == self.tenant_id,
            WhatsAppAgent.is_active == True
        ).group_by(
            WhatsAppAgent.id,
            WhatsAppAgent.name,
            WhatsAppAgent.email
        ).all()
        
        return [
            {
                "agent_id": str(row.id),
                "name": row.name,
                "email": row.email,
                "total_handoffs": row.total_handoffs or 0,
                "resolved": row.resolved or 0,
                "resolution_rate": (
                    (row.resolved / row.total_handoffs * 100)
                    if row.total_handoffs and row.total_handoffs > 0
                    else 0
                ),
                "avg_resolution_time_seconds": (
                    round(float(row.avg_resolution_time), 2)
                    if row.avg_resolution_time
                    else 0
                )
            }
            for row in performance
        ]
    
    def get_nps_score(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calcula NPS (Net Promoter Score) baseado em ratings
        
        NPS = % Promotores (9-10) - % Detratores (0-6)
        """
        
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Query para ratings
        ratings = self.db.query(
            WhatsAppSession.rating
        ).filter(
            WhatsAppSession.tenant_id == self.tenant_id,
            WhatsAppSession.rating.isnot(None),
            WhatsAppSession.started_at.between(start_date, end_date)
        ).all()
        
        if not ratings:
            return {
                "nps_score": 0,
                "total_responses": 0,
                "promoters": 0,
                "passives": 0,
                "detractors": 0
            }
        
        promoters = sum(1 for r in ratings if r.rating and r.rating >= 9)
        passives = sum(1 for r in ratings if r.rating and 7 <= r.rating <= 8)
        detractors = sum(1 for r in ratings if r.rating and r.rating <= 6)
        total = len(ratings)
        
        nps = ((promoters - detractors) / total * 100) if total > 0 else 0
        
        return {
            "nps_score": round(nps, 2),
            "total_responses": total,
            "promoters": promoters,
            "promoters_pct": round(promoters / total * 100, 2) if total > 0 else 0,
            "passives": passives,
            "passives_pct": round(passives / total * 100, 2) if total > 0 else 0,
            "detractors": detractors,
            "detractors_pct": round(detractors / total * 100, 2) if total > 0 else 0
        }
