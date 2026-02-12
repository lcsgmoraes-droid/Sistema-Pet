"""
Healthcheck e Readiness Check Routes - Pré-Prod Bloco 2
========================================================

Endpoints operacionais para monitoramento de infraestrutura seguindo
boas práticas de produção:

- /health: Liveness probe (processo está vivo?)
- /ready: Readiness probe (app está pronto para receber tráfego?)

Autor: Sistema Pet - Pré-Prod Block 2
Data: 2026-02-05
"""
from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
import logging

from app.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """
    Healthcheck básico (Liveness Probe)
    ====================================
    
    Verifica se o processo está vivo e respondendo.
    
    IMPORTANTE:
    - NÃO acessa banco de dados
    - NÃO acessa serviços externos
    - NÃO executa validações pesadas
    - Responde SEMPRE rápido (< 100ms)
    
    Uso:
    - Kubernetes liveness probe
    - Load balancer health check
    - Monitoramento básico
    
    Retorna:
        200 OK: Processo está rodando normalmente
    
    Exemplo de resposta:
        {
            "status": "ok"
        }
    """
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness_check(db: Session = Depends(get_session)):
    """
    Readiness check (Readiness Probe)
    =================================
    
    Verifica se a aplicação está PRONTA para receber requisições.
    
    Validações executadas:
    ----------------------
    1. Conexão com PostgreSQL (SELECT 1)
    2. Schema/Migrations aplicadas (tabela alembic_version existe)
    
    Uso:
    - Kubernetes readiness probe
    - Deploy health check
    - Validação pós-deployment
    
    Retorna:
        200 OK: Aplicação pronta
            {
                "status": "ready",
                "database": "connected",
                "migrations": "applied"
            }
        
        503 Service Unavailable: Aplicação não pronta
            {
                "status": "unavailable",
                "database": "error" | "connected",
                "migrations": "error" | "not_applied",
                "message": "Database connection failed" (sem dados sensíveis)
            }
    
    SEGURANÇA:
    - Mensagens de erro NÃO expõem dados sensíveis
    - Stack traces NÃO são retornados
    - Detalhes técnicos são logados, não expostos
    """
    
    checks = {
        "database": "unknown",
        "migrations": "unknown"
    }
    
    try:
        # ============================================================
        # CHECK 1: Conexão com PostgreSQL
        # ============================================================
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "connected"
            logger.debug("✓ Database connection OK")
        except Exception as db_error:
            checks["database"] = "error"
            logger.error(f"✗ Database connection failed: {str(db_error)}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unavailable",
                    "database": "error",
                    "migrations": "unknown",
                    "message": "Database connection failed"
                }
            )
        
        # ============================================================
        # CHECK 2: Schema/Migrations aplicadas
        # ============================================================
        try:
            # Verifica se a tabela alembic_version existe
            # (indica que migrations foram aplicadas)
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            if "alembic_version" in tables:
                # Verifica se existe alguma versão aplicada
                result = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                if result:
                    checks["migrations"] = "applied"
                    logger.debug(f"✓ Migrations OK (version: {result[0]})")
                else:
                    checks["migrations"] = "not_applied"
                    logger.warning("✗ No migration version found in alembic_version")
                    return JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={
                            "status": "unavailable",
                            "database": "connected",
                            "migrations": "not_applied",
                            "message": "Database migrations not applied"
                        }
                    )
            else:
                checks["migrations"] = "not_applied"
                logger.warning("✗ alembic_version table not found")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "unavailable",
                        "database": "connected",
                        "migrations": "not_applied",
                        "message": "Database schema not initialized"
                    }
                )
        
        except Exception as migration_error:
            checks["migrations"] = "error"
            logger.error(f"✗ Migration check failed: {str(migration_error)}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unavailable",
                    "database": "connected",
                    "migrations": "error",
                    "message": "Migration validation failed"
                }
            )
        
        # ============================================================
        # SUCESSO: Aplicação pronta
        # ============================================================
        logger.info("✅ Readiness check passed - application ready")
        return {
            "status": "ready",
            "database": "connected",
            "migrations": "applied"
        }
    
    except Exception as e:
        # Fallback para erros não capturados
        logger.error(f"✗ Unexpected error in readiness check: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "database": checks.get("database", "unknown"),
                "migrations": checks.get("migrations", "unknown"),
                "message": "Internal health check error"
            }
        )
