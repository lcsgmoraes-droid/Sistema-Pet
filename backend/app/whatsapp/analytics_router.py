# ============================================================================
# SPRINT 7: Analytics Router
# Endpoints para métricas, relatórios e análises avançadas
# ============================================================================

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.whatsapp.analytics import WhatsAppAnalyticsService
from pydantic import BaseModel, Field


router = APIRouter(prefix="/whatsapp/analytics", tags=["WhatsApp Analytics"])


async def _usuario_analytics(user_and_tenant=Depends(get_current_user_and_tenant)) -> User:
    return user_and_tenant[0]


class DateRangeQuery(BaseModel):
    """Query parameters para filtro de período"""
    start_date: Optional[datetime] = Field(
        None,
        description="Data inicial (ISO format). Padrão: 30 dias atrás"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Data final (ISO format). Padrão: agora"
    )


@router.get("/dashboard")
def get_dashboard_metrics(
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    current_user: User = Depends(_usuario_analytics)
):
    """
    📊 **Dashboard Completo de Métricas**
    
    Retorna visão geral completa incluindo:
    - Total de conversas e mensagens
    - Taxa de resolução automática
    - Tempo médio de resposta
    - Custo por conversa
    - Intenções mais comuns
    - Horários de pico
    - Distribuição de sentimentos
    - Estatísticas de handoffs
    - Uso de tools/ferramentas
    
    **Período padrão:** Últimos 30 dias
    """
    
    # Parse dates
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para start_date. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para end_date. Use YYYY-MM-DD")
    
    analytics = WhatsAppAnalyticsService(db, str(current_user.tenant_id))
    
    try:
        metrics = analytics.get_dashboard_metrics(start_date=start, end_date=end)
        return metrics
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar métricas: {str(e)}")


@router.get("/trends")
def get_conversation_trends(
    interval: str = Query(
        "day",
        description="Intervalo de agrupamento: hour, day, week, month"
    ),
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    current_user: User = Depends(_usuario_analytics)
):
    """
    📈 **Tendências de Conversas**
    
    Retorna séries temporais de:
    - Número de sessões por período
    - Custo total por período
    
    **Intervalos disponíveis:** hour, day, week, month
    """
    
    if interval not in ['hour', 'day', 'week', 'month']:
        raise HTTPException(
            400,
            "Intervalo inválido. Use: hour, day, week ou month"
        )
    
    # Parse dates
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para start_date")
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para end_date")
    
    analytics = WhatsAppAnalyticsService(db, str(current_user.tenant_id))
    
    try:
        trends = analytics.get_conversation_trends(
            start_date=start,
            end_date=end,
            interval=interval
        )
        return {"trends": trends, "interval": interval}
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar tendências: {str(e)}")


@router.get("/agents/performance")
def get_agent_performance(
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    current_user: User = Depends(_usuario_analytics)
):
    """
    👥 **Performance de Atendentes**
    
    Retorna métricas de cada atendente humano:
    - Total de handoffs atribuídos
    - Handoffs resolvidos
    - Taxa de resolução
    - Tempo médio de resolução
    
    **Útil para:** Avaliar produtividade, identificar treinamentos necessários
    """
    
    # Parse dates
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para start_date")
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para end_date")
    
    analytics = WhatsAppAnalyticsService(db, str(current_user.tenant_id))
    
    try:
        performance = analytics.get_agent_performance(
            start_date=start,
            end_date=end
        )
        return {"agents": performance}
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar performance: {str(e)}")


@router.get("/nps")
def get_nps_score(
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    current_user: User = Depends(_usuario_analytics)
):
    """
    ⭐ **Net Promoter Score (NPS)**
    
    Calcula NPS baseado em avaliações dos clientes:
    - **Promotores** (9-10): Clientes satisfeitos
    - **Neutros** (7-8): Clientes satisfeitos mas não entusiasmados
    - **Detratores** (0-6): Clientes insatisfeitos
    
    **Fórmula:** NPS = % Promotores - % Detratores
    
    **Benchmark:**
    - NPS > 50: Excelente
    - NPS 30-50: Bom
    - NPS 0-30: Razoável
    - NPS < 0: Precisa melhorar
    """
    
    # Parse dates
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para start_date")
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para end_date")
    
    analytics = WhatsAppAnalyticsService(db, str(current_user.tenant_id))
    
    try:
        nps = analytics.get_nps_score(start_date=start, end_date=end)
        
        # Adicionar classificação
        score = nps["nps_score"]
        if score > 50:
            classification = "Excelente"
        elif score >= 30:
            classification = "Bom"
        elif score >= 0:
            classification = "Razoável"
        else:
            classification = "Precisa Melhorar"
        
        nps["classification"] = classification
        
        return nps
    except Exception as e:
        raise HTTPException(500, f"Erro ao calcular NPS: {str(e)}")


@router.get("/handoffs")
def get_handoff_analysis(
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    current_user: User = Depends(_usuario_analytics)
):
    """
    🤝 **Análise de Handoffs**
    
    Análise detalhada de transferências para atendimento humano:
    - Total de handoffs
    - Distribuição por motivo
    - Distribuição por prioridade
    - Tempo médio de resolução
    
    **Útil para:** Identificar quando a IA precisa de ajuda, otimizar automação
    """
    
    # Parse dates
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para start_date")
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para end_date")
    
    analytics = WhatsAppAnalyticsService(db, str(current_user.tenant_id))
    
    try:
        handoff_data = analytics.get_handoff_analysis(
            start_date=start,
            end_date=end
        )
        return handoff_data
    except Exception as e:
        raise HTTPException(500, f"Erro ao analisar handoffs: {str(e)}")


@router.get("/costs")
def get_cost_analysis(
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    db: Session = Depends(get_session),
    current_user: User = Depends(_usuario_analytics)
):
    """
    💰 **Análise de Custos**
    
    Análise detalhada de custos com OpenAI:
    - Custo total por período
    - Tokens utilizados (input/output)
    - Custo por tipo de mensagem
    - Custo médio por conversa
    
    **Útil para:** Controle de budget, otimização de prompts
    """
    
    # Parse dates
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para start_date")
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para end_date")
    
    analytics = WhatsAppAnalyticsService(db, str(current_user.tenant_id))
    
    try:
        cost_data = analytics.get_cost_analysis(
            start_date=start,
            end_date=end
        )
        return cost_data
    except Exception as e:
        raise HTTPException(500, f"Erro ao analisar custos: {str(e)}")


@router.post("/export")
def export_report(
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    format: str = Query("json", description="Formato: json, csv, pdf"),
    db: Session = Depends(get_session),
    current_user: User = Depends(_usuario_analytics)
):
    """
    📥 **Exportar Relatório**
    
    Gera relatório completo de analytics em diferentes formatos:
    - **JSON**: Para integração com outros sistemas
    - **CSV**: Para análise em Excel/Google Sheets
    - **PDF**: Para apresentação executiva (futuro)
    
    **Inclui:** Todas as métricas de analytics consolidadas
    """
    
    # Parse dates
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para start_date")
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(400, "Formato de data inválido para end_date")
    
    if format not in ["json", "csv", "pdf"]:
        raise HTTPException(400, "Formato inválido. Use: json, csv ou pdf")
    
    analytics = WhatsAppAnalyticsService(db, str(current_user.tenant_id))
    
    try:
        # Coletar todas as métricas
        dashboard = analytics.get_dashboard_metrics(start_date=start, end_date=end)
        trends = analytics.get_conversation_trends(start_date=start, end_date=end)
        handoffs = analytics.get_handoff_analysis(start_date=start, end_date=end)
        costs = analytics.get_cost_analysis(start_date=start, end_date=end)
        
        report = {
            "format": format,
            "generated_at": datetime.utcnow().isoformat(),
            "period": dashboard["period"],
            "dashboard": dashboard,
            "trends": trends,
            "handoffs": handoffs,
            "costs": costs
        }
        
        if format == "json":
            return report
        elif format == "csv":
            # TODO: Converter para CSV
            raise HTTPException(501, "Exportação CSV será implementada em breve")
        elif format == "pdf":
            # TODO: Gerar PDF
            raise HTTPException(501, "Exportação PDF será implementada em breve")
            
    except Exception as e:
        raise HTTPException(500, f"Erro ao exportar relatório: {str(e)}")


@router.get("/summary")
def get_quick_summary(
    db: Session = Depends(get_session),
    current_user: User = Depends(_usuario_analytics)
):
    """
    ⚡ **Resumo Rápido (Últimas 24h)**
    
    Retorna métricas das últimas 24 horas:
    - Conversas iniciadas
    - Mensagens trocadas
    - Handoffs criados
    - Custo total
    - Taxa de resolução automática
    """
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)
    
    analytics = WhatsAppAnalyticsService(db, str(current_user.tenant_id))
    
    try:
        metrics = analytics.get_dashboard_metrics(
            start_date=start_date,
            end_date=end_date
        )
        
        # Retornar apenas overview
        return {
            "period": "Últimas 24 horas",
            "metrics": metrics["overview"]
        }
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar resumo: {str(e)}")
