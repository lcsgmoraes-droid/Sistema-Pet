"""
Health Check e Monitoring Endpoints
Fornece endpoints para verificação de saúde da aplicação e métricas
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any
import psutil
import time

from app.db import get_session
from app.whatsapp.models import WhatsAppSession, WhatsAppMessage

router = APIRouter(prefix="/health", tags=["Health & Monitoring"])


@router.get("")
async def health_check() -> Dict[str, Any]:
    """
    🏥 **Health Check Básico**
    
    Retorna status geral da aplicação.
    Usado por load balancers e monitoramento.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Pet Shop Pro - WhatsApp IA",
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health(db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    🔍 **Health Check Detalhado**
    
    Verifica saúde de todos os componentes:
    - Banco de dados
    - Memória
    - CPU
    - Disco
    """
    
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # 1. Database Check
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_latency = (time.time() - start_time) * 1000  # ms
        
        health_status["checks"]["database"] = {
            "status": "healthy",
            "latency_ms": round(db_latency, 2),
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed"
        }
    
    # 2. System Resources
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        disk = psutil.disk_usage('/')
        
        health_status["checks"]["system"] = {
            "status": "healthy",
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            },
            "cpu": {
                "percent": cpu_percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent": disk.percent
            }
        }
        
        # Alertas
        if memory.percent > 90:
            health_status["status"] = "degraded"
            health_status["checks"]["system"]["warning"] = "High memory usage"
        
        if cpu_percent > 90:
            health_status["status"] = "degraded"
            health_status["checks"]["system"]["warning"] = "High CPU usage"
            
        if disk.percent > 90:
            health_status["status"] = "degraded"
            health_status["checks"]["system"]["warning"] = "High disk usage"
            
    except Exception as e:
        health_status["checks"]["system"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # 3. Application Metrics
    try:
        # Sessões ativas
        active_sessions = db.query(WhatsAppSession).filter(
            WhatsAppSession.status == 'active'
        ).count()
        
        # Total de mensagens hoje
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        messages_today = db.query(WhatsAppMessage).filter(
            WhatsAppMessage.created_at >= today_start
        ).count()
        
        health_status["checks"]["application"] = {
            "status": "healthy",
            "metrics": {
                "active_sessions": active_sessions,
                "messages_today": messages_today
            }
        }
        
    except Exception as e:
        health_status["checks"]["application"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    return health_status


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    ✅ **Readiness Check**
    
    Verifica se a aplicação está pronta para receber tráfego.
    Usado por Kubernetes/Docker para inicialização.
    """
    from sqlalchemy import text
    
    try:
        # Testa conexão com banco com timeout implícito
        result = db.execute(text("SELECT 1")).fetchone()
        if result is None:
            raise Exception("Database query returned no result")
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": "ok"
            }
        }
    except Exception as e:
        # Retorna 200 com ready=False ao invés de 503
        # Isso permite que o sistema ainda responda mas indique não estar pronto
        return {
            "ready": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "checks": {
                "database": "failed"
            }
        }


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    💓 **Liveness Check**
    
    Verifica se a aplicação está "viva" (respondendo).
    Usado por Kubernetes/Docker para restart.
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def application_metrics(db: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    📊 **Application Metrics**
    
    Métricas da aplicação em formato estruturado.
    Compatível com Prometheus.
    """
    
    try:
        # Sessões
        total_sessions = db.query(WhatsAppSession).count()
        active_sessions = db.query(WhatsAppSession).filter(
            WhatsAppSession.status == 'active'
        ).count()
        
        # Mensagens
        total_messages = db.query(WhatsAppMessage).count()
        
        # Por período (últimas 24h)
        day_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        sessions_24h = db.query(WhatsAppSession).filter(
            WhatsAppSession.started_at >= day_ago
        ).count()
        messages_24h = db.query(WhatsAppMessage).filter(
            WhatsAppMessage.created_at >= day_ago
        ).count()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "sessions": {
                    "total": total_sessions,
                    "active": active_sessions,
                    "last_24h": sessions_24h
                },
                "messages": {
                    "total": total_messages,
                    "last_24h": messages_24h
                },
                "system": {
                    "memory_percent": psutil.virtual_memory().percent,
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "disk_percent": psutil.disk_usage('/').percent
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect metrics: {str(e)}"
        )


@router.get("/prometheus")
async def prometheus_metrics(db: Session = Depends(get_session)) -> str:
    """
    🔥 **Prometheus Metrics**
    
    Expõe métricas no formato Prometheus.
    """
    
    try:
        # Coleta métricas
        total_sessions = db.query(WhatsAppSession).count()
        active_sessions = db.query(WhatsAppSession).filter(
            WhatsAppSession.status == 'active'
        ).count()
        total_messages = db.query(WhatsAppMessage).count()
        
        # Formato Prometheus
        metrics = f"""# HELP whatsapp_sessions_total Total number of WhatsApp sessions
# TYPE whatsapp_sessions_total counter
whatsapp_sessions_total {total_sessions}

# HELP whatsapp_sessions_active Number of active WhatsApp sessions
# TYPE whatsapp_sessions_active gauge
whatsapp_sessions_active {active_sessions}

# HELP whatsapp_messages_total Total number of WhatsApp messages
# TYPE whatsapp_messages_total counter
whatsapp_messages_total {total_messages}

# HELP system_memory_usage_percent System memory usage percentage
# TYPE system_memory_usage_percent gauge
system_memory_usage_percent {psutil.virtual_memory().percent}

# HELP system_cpu_usage_percent System CPU usage percentage
# TYPE system_cpu_usage_percent gauge
system_cpu_usage_percent {psutil.cpu_percent(interval=0.1)}

# HELP system_disk_usage_percent System disk usage percentage
# TYPE system_disk_usage_percent gauge
system_disk_usage_percent {psutil.disk_usage('/').percent}
"""
        
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Prometheus metrics: {str(e)}"
        )
