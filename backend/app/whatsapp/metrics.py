"""
Serviço de Métricas - Coleta e análise de dados de uso
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import json
import logging

from app.whatsapp.models import WhatsAppMetric, WhatsAppMessage, WhatsAppSession

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Coleta e armazena métricas de uso"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    def record_message_processed(
        self,
        intent: str,
        processing_time: float,
        tokens_used: int,
        model_used: str,
        success: bool = True
    ):
        """Registra processamento de mensagem"""
        try:
            metric = WhatsAppMetric(
                tenant_id=self.tenant_id,
                metric_type="message_processed",
                value=1.0,
                metric_metadata=json.dumps({
                    "intent": intent,
                    "processing_time_seconds": processing_time,
                    "tokens_used": tokens_used,
                    "model_used": model_used,
                    "success": success
                })
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar métrica: {e}")
            self.db.rollback()
    
    def record_tool_call(
        self,
        tool_name: str,
        execution_time: float,
        success: bool = True
    ):
        """Registra chamada de tool"""
        try:
            metric = WhatsAppMetric(
                tenant_id=self.tenant_id,
                metric_type="tool_call",
                value=1.0,
                metric_metadata=json.dumps({
                    "tool_name": tool_name,
                    "execution_time_seconds": execution_time,
                    "success": success
                })
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar tool call: {e}")
            self.db.rollback()
    
    def record_human_handoff(
        self,
        reason: str,
        session_id: str
    ):
        """Registra transferência para humano"""
        try:
            metric = WhatsAppMetric(
                tenant_id=self.tenant_id,
                metric_type="human_handoff",
                value=1.0,
                metric_metadata=json.dumps({
                    "reason": reason,
                    "session_id": session_id
                })
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar handoff: {e}")
            self.db.rollback()
    
    def record_conversation_resolved(
        self,
        session_id: str,
        messages_count: int,
        duration_minutes: float,
        resolved_by: str = "ai"  # "ai" ou "human"
    ):
        """Registra conversa finalizada"""
        try:
            metric = WhatsAppMetric(
                tenant_id=self.tenant_id,
                metric_type="conversation_resolved",
                value=1.0,
                metric_metadata=json.dumps({
                    "session_id": session_id,
                    "messages_count": messages_count,
                    "duration_minutes": duration_minutes,
                    "resolved_by": resolved_by
                })
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar resolução: {e}")
            self.db.rollback()
    
    def record_api_cost(
        self,
        cost_usd: float,
        tokens_input: int,
        tokens_output: int,
        model: str
    ):
        """Registra custo de API"""
        try:
            metric = WhatsAppMetric(
                tenant_id=self.tenant_id,
                metric_type="api_cost",
                value=cost_usd,
                metric_metadata=json.dumps({
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                    "model": model
                })
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar custo: {e}")
            self.db.rollback()


class MetricsAnalyzer:
    """Analisa métricas coletadas"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    def get_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Retorna resumo de métricas"""
        
        # Defaults: últimos 30 dias
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Buscar métricas do período
        metrics_query = self.db.query(WhatsAppMetric).filter(
            WhatsAppMetric.tenant_id == self.tenant_id,
            WhatsAppMetric.timestamp >= start_date,
            WhatsAppMetric.timestamp <= end_date
        )
        
        # Total de mensagens processadas
        messages_processed = metrics_query.filter(
            WhatsAppMetric.metric_type == "message_processed"
        ).count()
        
        # Total de transferências para humano
        human_handoffs = metrics_query.filter(
            WhatsAppMetric.metric_type == "human_handoff"
        ).count()
        
        # Total de conversas resolvidas
        conversations_resolved = metrics_query.filter(
            WhatsAppMetric.metric_type == "conversation_resolved"
        ).count()
        
        # Custo total
        total_cost = self.db.query(func.sum(WhatsAppMetric.value)).filter(
            WhatsAppMetric.tenant_id == self.tenant_id,
            WhatsAppMetric.metric_type == "api_cost",
            WhatsAppMetric.timestamp >= start_date,
            WhatsAppMetric.timestamp <= end_date
        ).scalar() or 0.0
        
        # Calcular taxa de resolução automática
        resolution_rate = 0.0
        if conversations_resolved > 0:
            auto_resolved = self._count_auto_resolved_conversations(start_date, end_date)
            resolution_rate = (auto_resolved / conversations_resolved) * 100
        
        # Tempo médio de resposta
        avg_response_time = self._get_average_response_time(start_date, end_date)
        
        # Intenções mais comuns
        top_intents = self._get_top_intents(start_date, end_date, limit=5)
        
        # Horários de pico
        peak_hours = self._get_peak_hours(start_date, end_date)
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "totals": {
                "messages_processed": messages_processed,
                "human_handoffs": human_handoffs,
                "conversations_resolved": conversations_resolved,
                "total_cost_usd": round(total_cost, 2)
            },
            "rates": {
                "auto_resolution_rate": round(resolution_rate, 2),
                "handoff_rate": round((human_handoffs / messages_processed * 100), 2) if messages_processed > 0 else 0
            },
            "performance": {
                "avg_response_time_seconds": round(avg_response_time, 2)
            },
            "insights": {
                "top_intents": top_intents,
                "peak_hours": peak_hours
            }
        }
    
    def _count_auto_resolved_conversations(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """Conta conversas resolvidas automaticamente"""
        try:
            metrics = self.db.query(WhatsAppMetric).filter(
                WhatsAppMetric.tenant_id == self.tenant_id,
                WhatsAppMetric.metric_type == "conversation_resolved",
                WhatsAppMetric.timestamp >= start_date,
                WhatsAppMetric.timestamp <= end_date
            ).all()
            
            auto_count = 0
            for metric in metrics:
                try:
                    metadata = json.loads(metric.metric_metadata)
                    if metadata.get("resolved_by") == "ai":
                        auto_count += 1
                except:
                    pass
            
            return auto_count
        except Exception as e:
            logger.error(f"Erro ao contar conversas auto-resolvidas: {e}")
            return 0
    
    def _get_average_response_time(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calcula tempo médio de resposta"""
        try:
            metrics = self.db.query(WhatsAppMetric).filter(
                WhatsAppMetric.tenant_id == self.tenant_id,
                WhatsAppMetric.metric_type == "message_processed",
                WhatsAppMetric.timestamp >= start_date,
                WhatsAppMetric.timestamp <= end_date
            ).all()
            
            if not metrics:
                return 0.0
            
            total_time = 0.0
            count = 0
            
            for metric in metrics:
                try:
                    metadata = json.loads(metric.metric_metadata)
                    processing_time = metadata.get("processing_time_seconds", 0)
                    total_time += processing_time
                    count += 1
                except:
                    pass
            
            return total_time / count if count > 0 else 0.0
        except Exception as e:
            logger.error(f"Erro ao calcular tempo médio: {e}")
            return 0.0
    
    def _get_top_intents(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retorna intenções mais comuns"""
        try:
            metrics = self.db.query(WhatsAppMetric).filter(
                WhatsAppMetric.tenant_id == self.tenant_id,
                WhatsAppMetric.metric_type == "message_processed",
                WhatsAppMetric.timestamp >= start_date,
                WhatsAppMetric.timestamp <= end_date
            ).all()
            
            intent_counts = {}
            
            for metric in metrics:
                try:
                    metadata = json.loads(metric.metric_metadata)
                    intent = metadata.get("intent", "desconhecido")
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1
                except:
                    pass
            
            # Ordenar e retornar top N
            sorted_intents = sorted(
                intent_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:limit]
            
            return [
                {"intent": intent, "count": count}
                for intent, count in sorted_intents
            ]
        except Exception as e:
            logger.error(f"Erro ao buscar top intents: {e}")
            return []
    
    def _get_peak_hours(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Retorna horários de pico"""
        try:
            metrics = self.db.query(WhatsAppMetric).filter(
                WhatsAppMetric.tenant_id == self.tenant_id,
                WhatsAppMetric.metric_type == "message_processed",
                WhatsAppMetric.timestamp >= start_date,
                WhatsAppMetric.timestamp <= end_date
            ).all()
            
            hour_counts = {}
            
            for metric in metrics:
                hour = metric.timestamp.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            # Retornar top 3 horários
            sorted_hours = sorted(
                hour_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            return [
                {"hour": f"{hour:02d}:00", "messages": count}
                for hour, count in sorted_hours
            ]
        except Exception as e:
            logger.error(f"Erro ao buscar horários de pico: {e}")
            return []
    
    def get_intent_breakdown(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Retorna breakdown completo de intenções"""
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        return dict(self._get_top_intents(start_date, end_date, limit=100))
    
    def get_cost_breakdown(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Retorna breakdown de custos por modelo"""
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        try:
            metrics = self.db.query(WhatsAppMetric).filter(
                WhatsAppMetric.tenant_id == self.tenant_id,
                WhatsAppMetric.metric_type == "api_cost",
                WhatsAppMetric.timestamp >= start_date,
                WhatsAppMetric.timestamp <= end_date
            ).all()
            
            model_costs = {}
            total_tokens = {"input": 0, "output": 0}
            
            for metric in metrics:
                try:
                    metadata = json.loads(metric.metric_metadata)
                    model = metadata.get("model", "unknown")
                    cost = metric.value
                    
                    if model not in model_costs:
                        model_costs[model] = {
                            "cost": 0.0,
                            "tokens_input": 0,
                            "tokens_output": 0,
                            "calls": 0
                        }
                    
                    model_costs[model]["cost"] += cost
                    model_costs[model]["tokens_input"] += metadata.get("tokens_input", 0)
                    model_costs[model]["tokens_output"] += metadata.get("tokens_output", 0)
                    model_costs[model]["calls"] += 1
                    
                    total_tokens["input"] += metadata.get("tokens_input", 0)
                    total_tokens["output"] += metadata.get("tokens_output", 0)
                except:
                    pass
            
            return {
                "by_model": model_costs,
                "total_tokens": total_tokens
            }
        except Exception as e:
            logger.error(f"Erro ao calcular custos: {e}")
            return {"by_model": {}, "total_tokens": {"input": 0, "output": 0}}


# Factory functions
def get_metrics_collector(db: Session, tenant_id: str) -> MetricsCollector:
    """Cria instância do MetricsCollector"""
    return MetricsCollector(db, tenant_id)


def get_metrics_analyzer(db: Session, tenant_id: str) -> MetricsAnalyzer:
    """Cria instância do MetricsAnalyzer"""
    return MetricsAnalyzer(db, tenant_id)
