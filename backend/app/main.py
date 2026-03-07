"""
Sistema Pet Shop Pro - Backend API
FastAPI + SQLAlchemy + SQLite/PostgreSQL
"""
import app.database.orm_guards  # ✅ ORM Guards: força IDs=None antes do flush

from typing import Optional
import threading
import time
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app import db
from app.db import get_session as get_db
from app.db.migration_check import ensure_db_ready  # Pré-Prod Block 3: verificação de migrations
from app.config import (
    SYSTEM_NAME,
    SYSTEM_VERSION,
    ALLOWED_ORIGINS,
    print_config,
    ENVIRONMENT,
    DEBUG,
    DATABASE_URL,
    JWT_SECRET_KEY,
    GOOGLE_MAPS_API_KEY,
    settings,  # Pré-Prod Block 1: objeto de settings completo
)
from app.core.settings_validation import validate_settings  # Pré-Prod Block 1: validação de settings
from app.utils.logger import generate_trace_id, set_trace_id, set_endpoint, get_trace_id, clear_context, configure_logging
from app.auth_routes_multitenant import router as auth_router
from app.clientes_routes import router as clientes_router
from app.pets_routes import router as pets_router  # Módulo dedicado de pets
from app.cadastros_routes import router as cadastros_router  # Espécies e Raças
from app.produtos_routes import router as produtos_router
from app.variacoes_routes import router as variacoes_router  # Sprint 2: Variações
from app.vendas_routes import router as vendas_router
from app.caixa_routes import router as caixa_router
from app.nfe_routes import router as nfe_router
from app.estoque_routes import router as estoque_router
from app.estoque_alertas_routes import router as estoque_alertas_router
from app.bling_sync_routes import router as bling_sync_router
from app.pedidos_compra_routes import router as pedidos_compra_router
from app.notas_entrada_routes import router as notas_entrada_router
from app.contas_pagar_routes import router as contas_pagar_router
from app.contas_receber_routes import router as contas_receber_router
from app.conciliacao_cartao_routes import router as conciliacao_cartao_router
from app.conciliacao_routes import router as conciliacao_router
from app.conciliacao_bancaria_routes import router as conciliacao_bancaria_router
from app.conciliacao_aba1_routes import router as conciliacao_aba1_router
from app.conciliacao_historico_routes import router as conciliacao_historico_router
from app.stone_routes import router as stone_router
from app.financeiro_routes import router as financeiro_router
from app.contas_bancarias_routes import router as contas_bancarias_router
from app.admin_routes import router as admin_router
from app.lancamentos_routes import router as lancamentos_router
from app.categorias_routes import router as categorias_router
from app.bling_routes import router as bling_router
from app.bling_oauth_routes import router as bling_oauth_router
from app.integracao_bling_pedido_routes import router as bling_pedido_router
from app.integracao_bling_nf_routes import router as bling_nf_router
from app.dashboard_routes import router as dashboard_router
from app.relatorio_vendas_routes import router as relatorio_vendas_router
from app.dre_routes import router as dre_router
from app.dre_canais_routes import router as dre_canais_router
from app.dre_plano_contas_routes import router as dre_plano_contas_router
from app.dre_classificacao_routes import router as dre_classificacao_router
from app.ia_routes import router as ia_router
from app.chat_routes import router as chat_router
from app.dre_ia_routes import router as dre_ia_router
from app.ia.aba7_extrato_routes import router as extrato_ia_router
from app.ia_fluxo_routes import router as ia_fluxo_router
from app.tributacao_routes import router as tributacao_router
from app.importacao_produtos import router as importacao_router
from app.importacao_pessoas import router as importacao_pessoas_router
from app.lembretes import router as lembretes_router
from app.calculadora_racao import router as calculadora_racao_router
from app.cliente_info_pdv import router as cliente_info_pdv_router
from app.opcoes_racao_routes import router as opcoes_racao_router
from app.analise_racoes_routes import router as analise_racoes_router  # Fase 4: Análises de Rações
from app.pdv_racoes_routes import router as pdv_racoes_router  # Fase 5: PDV Inteligente de Rações
from app.sugestoes_racoes_routes import router as sugestoes_racoes_router  # Fase 6: Sugestões Inteligentes
from app.ml_racoes_routes import router as ml_racoes_router  # Fase 7: Machine Learning
from app.formas_pagamento_routes import router as formas_pagamento_router
from app.operadoras_routes import router as operadoras_router
from app.comissoes_routes import router as comissoes_router
from app.analytics.api import router as analytics_router
from app.comissoes_demonstrativo_routes import router as comissoes_demonstrativo_router
from app.comissoes_avancadas_routes import router as comissoes_avancadas_router
from app.comissoes_diagnostico_routes import router as comissoes_diagnostico_router
from app.routers.relatorios_comissoes import router as relatorios_comissoes_router
from app.routes.acertos_routes import router as acertos_router
from app.audit.api import router as audit_router
from app.api.endpoints.whatsapp import router as whatsapp_router  # Sprint 3: WhatsApp IA
# from app.api.endpoints.whatsapp import router as whatsapp_router  # DESATIVADO - Conflita com novos modelos WhatsApp IA
from app.api.endpoints.segmentacao import router as segmentacao_router
from app.pdv_ai_routes import router as pdv_ai_router
from app.usuarios_routes import router as usuarios_router
from app.roles_routes import router as roles_router
from app.permissions_routes import router as permissions_router
from app.api.pdv_internal_routes import router as pdv_internal_router
# [DESATIVADO - PHASE 5] from app.api.opportunity_metrics_routes import router as opportunity_metrics_router
from app.api.racao_calculadora_routes import router as racao_calculadora_internal_router
from app.api.v1.fiscal_sugestao import router as fiscal_sugestao_router
from app.api.v1.produto_fiscal import router as produto_fiscal_router
from app.api.v1.pdv_fiscal import router as pdv_fiscal_router
from app.api.v1.produto_fiscal_v2 import router as produto_fiscal_v2_router
from app.api.v1.empresa_fiscal import router as empresa_fiscal_router
from app.simples_routes import router as simples_router
from app.auditoria_provisoes_routes import router as auditoria_provisoes_router
from app.projecao_caixa_routes import router as projecao_caixa_router
from app.simulacao_contratacao_routes import router as simulacao_contratacao_router
from app.cargos_routes import router as cargos_router
from app.funcionarios_routes import router as funcionarios_router
from app.empresa_config_routes import router as empresa_config_router
from app.pdv_indicadores_routes import router as pdv_indicadores_router
from app.empresa_routes import router as empresa_router
from app.api.endpoints.configuracoes_entrega import router as configuracoes_entrega_router
from app.api.endpoints.rotas_entrega import router as rotas_entrega_router
from app.api.endpoints.acertos_entrega import router as acertos_entrega_router
from app.api.endpoints.configuracao_custo_moto import router as configuracao_custo_moto_router
from app.api.endpoints.dashboard_entregas import router as dashboard_entregas_router  # ETAPA 11.1
from app.pendencia_estoque_routes import router as pendencia_estoque_router  # Sistema de Lista de Espera

# ============================================================================
# WHATSAPP + IA - SPRINT 2 & 4 & 6 & 7
# ============================================================================
from app.whatsapp.webhook import router as whatsapp_webhook_router
from app.routers.whatsapp_config import router as whatsapp_config_router
from app.routers.whatsapp_handoff import router as whatsapp_handoff_router  # Sprint 4
from app.routers.whatsapp_websocket import router as whatsapp_websocket_router  # Sprint 5: WebSocket
from app.routes.whatsapp_routes import router as whatsapp_api_router  # Sprint 6: Tools & Tests
from app.whatsapp.analytics_router import router as whatsapp_analytics_router  # Sprint 7: Analytics
from app.whatsapp.security_router import router as whatsapp_security_router  # Sprint 8: Security & LGPD
from app.health_router import router as health_router  # Sprint 9: Health & Monitoring
from app.admin_fix_routes import router as admin_fix_router  # Correções administrativas
from app.routes.health_routes import router as health_check_router  # FASE 8: Healthcheck + Readiness

# ============================================================================
# E-COMMERCE - Loja Pública
# ============================================================================
from app.routes.ecommerce import router as ecommerce_router
from app.routes.ecommerce_auth import router as ecommerce_auth_router
from app.routes.ecommerce_public import router as ecommerce_public_router
from app.routes.ecommerce_cart import router as ecommerce_cart_router
from app.routes.ecommerce_checkout import router as ecommerce_checkout_router
from app.routes.app_mobile_routes import router as app_mobile_router
from app.routes.ecommerce_webhooks import router as ecommerce_webhooks_router
from app.routes.ecommerce_aparencia_routes import router as ecommerce_aparencia_router
from app.routes.ecommerce_config_routes import router as ecommerce_config_router
from app.routes.ecommerce_notify_routes import router as ecommerce_notify_router
from app.routes.ecommerce_analytics_routes import router as ecommerce_analytics_router
from app.routes.ecommerce_entregador import router as ecommerce_entregador_router
from app.pedido_models import Pedido  # Modelo base ecommerce

# ============================================================================
# CAMPANHAS — Motor de Campanhas (Fase 1)
# ============================================================================
from app.campaigns.routes import router as campaigns_router

from app.tenancy.middleware import TenancyMiddleware
import logging
from pathlib import Path

# Importar modelos para registrar no SQLAlchemy (IMPORTANTE: antes de criar o app)
from app.models import User, UserSession, AuditLog, AcertoParceiro, EmailTemplate, EmailEnvio  # Modelos principais (removido WhatsAppMessage antigo)
from app.produtos_models import Lembrete  # Modelo de lembretes
from app.idempotency_models import IdempotencyKey  # Modelo de idempotência
from app.models_configuracao_custo_moto import ConfiguracaoCustoMoto  # ETAPA 8.2 - Custos da Moto
from app.pendencia_estoque_models import PendenciaEstoque  # Sistema de Lista de Espera
from app.ia.aba7_extrato_models import (
    PadraoCategoriacaoIA,
    LancamentoImportado,
    ArquivoExtratoImportado,
    HistoricoAtualizacaoDRE,
    ConfiguracaoTributaria
)
from app.ia.aba7_models import DREPeriodo, DREProduto

# WHATSAPP + IA - NOVOS MODELOS (Sprint 2)
from app.whatsapp.models import (
    TenantWhatsAppConfig,
    WhatsAppSession,
    WhatsAppMessage,
    WhatsAppMetric
)
from app.whatsapp.models_handoff import WhatsAppAgent, WhatsAppHandoff  # Sprint 4: Handoff models

# ============================================================================
# CONFIGURAR LOGGING ESTRUTURADO GLOBAL
# ============================================================================

configure_logging()  # Configura formato estruturado para produção

# Configurar logging (legado)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


BLING_TOKEN_RENOVACAO_INTERVALO_SEGUNDOS = 5 * 60 * 60  # 5 horas
_bling_token_stop_event = threading.Event()
_bling_token_thread: Optional[threading.Thread] = None

# Job de expiração de reservas de pedidos Bling vencidos
_expirar_reservas_stop_event = threading.Event()
_expirar_reservas_thread: Optional[threading.Thread] = None
EXPIRAR_RESERVAS_INTERVALO_SEGUNDOS = 30 * 60  # 30 minutos

# Campaign Engine — scheduler APScheduler
_campaign_scheduler = None

# Arquivos usados para coordenar renovação entre os múltiplos workers uvicorn
_BLING_LOCK_FILE = "/tmp/bling_token_renewal.lock"
_BLING_LAST_RENEWAL_FILE = "/tmp/bling_token_last_renewal.txt"
# Janela de segurança: se outro worker renovou há menos de 60s, apenas recarrega do .env
_BLING_RENEWAL_COOLDOWN = 60


def _bling_recarregar_tokens_do_env():
    """Relê o access_token e refresh_token do .env e atualiza os.environ."""
    import os as _os
    try:
        from dotenv import dotenv_values
        env_path = "/opt/petshop/.env"
        if _os.path.exists(env_path):
            vals = dotenv_values(env_path)
            if vals.get("BLING_ACCESS_TOKEN"):
                _os.environ["BLING_ACCESS_TOKEN"] = vals["BLING_ACCESS_TOKEN"]
            if vals.get("BLING_REFRESH_TOKEN"):
                _os.environ["BLING_REFRESH_TOKEN"] = vals["BLING_REFRESH_TOKEN"]
    except Exception as e:
        logger.warning(f"[BLING] ⚠️ Erro ao recarregar tokens do .env: {e}")


def _loop_renovacao_token_bling():
    """
    Loop em background para renovar token Bling periodicamente.
    Usa um arquivo de lock para garantir que apenas um dos múltiplos
    workers uvicorn execute a renovação — os demais apenas recarregam
    o token atualizado do .env.
    """
    import os as _os
    worker_pid = _os.getpid()
    logger.info(f"[BLING] Job de renovação automática iniciado (PID {worker_pid}, intervalo: 5h)")

    while not _bling_token_stop_event.is_set():
        try:
            # Tenta importar fcntl (disponível no Linux/servidor)
            try:
                import fcntl
                has_fcntl = True
            except ImportError:
                has_fcntl = False

            if has_fcntl:
                # Coordenação via file lock entre workers
                with open(_BLING_LOCK_FILE, "w") as lock_f:
                    fcntl.flock(lock_f, fcntl.LOCK_EX)
                    try:
                        now = time.time()
                        recently_renewed = False
                        if _os.path.exists(_BLING_LAST_RENEWAL_FILE):
                            try:
                                with open(_BLING_LAST_RENEWAL_FILE, "r") as tf:
                                    last_ts = float(tf.read().strip())
                                if now - last_ts < _BLING_RENEWAL_COOLDOWN:
                                    recently_renewed = True
                            except Exception:
                                pass

                        if recently_renewed:
                            logger.info(f"[BLING] PID {worker_pid} — token já renovado por outro worker, recarregando do .env")
                            _bling_recarregar_tokens_do_env()
                        else:
                            from app.bling_integration import BlingAPI
                            bling = BlingAPI()
                            bling.renovar_access_token()
                            with open(_BLING_LAST_RENEWAL_FILE, "w") as tf:
                                tf.write(str(time.time()))
                            logger.info(f"[BLING] ✅ PID {worker_pid} — Token renovado automaticamente")
                    finally:
                        fcntl.flock(lock_f, fcntl.LOCK_UN)
            else:
                # Ambiente de desenvolvimento (Windows) — renova diretamente
                from app.bling_integration import BlingAPI
                bling = BlingAPI()
                bling.renovar_access_token()
                logger.info(f"[BLING] ✅ Token renovado automaticamente")

        except Exception as e:
            logger.warning(f"[BLING] ⚠️ PID {worker_pid} — Falha na renovação automática do token: {e}")

        _bling_token_stop_event.wait(BLING_TOKEN_RENOVACAO_INTERVALO_SEGUNDOS)

    logger.info(f"[BLING] Job de renovação automática finalizado (PID {worker_pid})")


def _loop_expirar_reservas():
    """
    Job em background para expirar reservas de pedidos Bling vencidos.
    Roda a cada 30 minutos e marca como 'expirado' todos os pedidos
    com status='aberto' cuja expira_em já passou, liberando o estoque reservado.
    """
    from datetime import datetime as _dt
    import os as _os
    worker_pid = _os.getpid()
    logger.info(f"[RESERVAS] Job de expiração de reservas iniciado (PID {worker_pid}, intervalo: 30min)")

    # Aguarda 2 minutos no startup para o backend estar totalmente pronto
    _expirar_reservas_stop_event.wait(120)

    while not _expirar_reservas_stop_event.is_set():
        try:
            from app.db import SessionLocal
            from app.pedido_integrado_models import PedidoIntegrado
            from app.pedido_integrado_item_models import PedidoIntegradoItem

            db = SessionLocal()
            try:
                agora = _dt.utcnow()
                pedidos_vencidos = db.query(PedidoIntegrado).filter(
                    PedidoIntegrado.status == "aberto",
                    PedidoIntegrado.expira_em < agora
                ).all()

                if pedidos_vencidos:
                    logger.info(f"[RESERVAS] {len(pedidos_vencidos)} pedido(s) vencido(s) para expirar")

                for pedido in pedidos_vencidos:
                    # Libera apenas os itens ainda reservados (sem liberado_em nem vendido_em)
                    itens = db.query(PedidoIntegradoItem).filter(
                        PedidoIntegradoItem.pedido_integrado_id == pedido.id,
                        PedidoIntegradoItem.liberado_em.is_(None),
                        PedidoIntegradoItem.vendido_em.is_(None)
                    ).all()
                    for item in itens:
                        item.liberado_em = agora
                        db.add(item)

                    pedido.status = "expirado"
                    db.add(pedido)

                if pedidos_vencidos:
                    db.commit()
                    logger.info(f"[RESERVAS] ✅ {len(pedidos_vencidos)} pedido(s) expirado(s), reservas liberadas")

            except Exception as e:
                db.rollback()
                logger.warning(f"[RESERVAS] ⚠️ Erro ao expirar reservas: {e}")
            finally:
                db.close()

        except Exception as e:
            logger.warning(f"[RESERVAS] ⚠️ PID {worker_pid} — Falha geral no job de expiração: {e}")

        _expirar_reservas_stop_event.wait(EXPIRAR_RESERVAS_INTERVALO_SEGUNDOS)

    logger.info(f"[RESERVAS] Job de expiração de reservas finalizado (PID {worker_pid})")


# ============================================================================
# CONFIGURAR SISTEMA DE EVENTOS DE DOMÍNIO
# ============================================================================

try:
    from app.domain.events.setup import setup_event_handlers
    from app.db import get_session

    # Configurar handlers de eventos
    setup_event_handlers(db_session_factory=get_session)
    logger.info("✅ Sistema de eventos de domínio configurado")

except Exception as e:
    logger.warning(f"⚠️  Não foi possível configurar sistema de eventos: {str(e)}")
    # Não aborta a inicialização

# ============================================================================
# RATE LIMITER E FASTAPI APP
# ============================================================================

# Configurar Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])

# Criar app
app = FastAPI(
    title=SYSTEM_NAME,
    description="Sistema completo de gestão para Pet Shop",
    version=SYSTEM_VERSION,
)

# ====================
# PROXY HEADERS - Para HTTPS atrás de reverse proxy (nginx)
# ====================
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# Confia nos headers X-Forwarded-* do nginx
@app.middleware("http")
async def proxy_headers_middleware(request: Request, call_next):
    """Respeita X-Forwarded-Proto para redirects HTTPS"""
    # Se nginx enviou X-Forwarded-Proto: https, o FastAPI deve usar HTTPS nos redirects
    if request.headers.get("X-Forwarded-Proto") == "https":
        request.scope["scheme"] = "https"
    response = await call_next(request)
    return response

# ====================
# MIDDLEWARE DE REQUEST CONTEXT (PRÉ-PROD BLOCO 4)
# ====================

# REMOVIDO: TraceIDMiddleware (substituído por RequestContextMiddleware)
# O novo middleware fornece:
# - request_id (UUID)
# - propagação via contextvars
# - logging estruturado com contexto completo
# - correlação de logs por request

# ====================
# MIDDLEWARES - ORDEM DE EXECUÇÃO
# ====================

# 1️⃣ Request Context (Pré-Prod Bloco 4) - request_id e observabilidade
from app.middlewares.request_context import RequestContextMiddleware
app.add_middleware(RequestContextMiddleware)

# 2️⃣ Security Audit - detecção de ataques (SQL injection, XSS, etc)
from app.middlewares.security_audit import SecurityAuditMiddleware
app.add_middleware(SecurityAuditMiddleware)

# 3️⃣ Request Logging (legacy) - mantido para compatibilidade
from app.middlewares.request_logging import RequestLoggingMiddleware
app.add_middleware(RequestLoggingMiddleware)

# 4️⃣ Rate Limit - protege contra brute force e spam
from app.middlewares.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# ====================
# MIDDLEWARES DE TENANT - MULTI-CAMADA
# ====================

# 🔒 CAMADA 1: Isolamento de contexto entre requests
# Garante que cada request tenha seu próprio contexto limpo
from app.tenancy.context import TenantContextMiddleware
app.add_middleware(TenantContextMiddleware)

# 🔒 CAMADA 2: Segurança Global de Tenant (NOVO - REFORÇADO)
# Valida tenant_id em TODAS as requests autenticadas
# Bloqueia requests com JWT sem tenant_id
from app.middlewares.tenant_middleware import TenantSecurityMiddleware
app.add_middleware(TenantSecurityMiddleware)

# 🔒 CAMADA 3: Tenant context com fallback (LEGADO - COMPATIBILIDADE)
# Mantido para compatibilidade, mas TenantSecurityMiddleware é mais restritivo
app.add_middleware(TenancyMiddleware)

# Adicionar rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Handler customizado para rate limit
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"🚫 Rate limit exceeded: {get_remote_address(request)} on {request.url.path}")
    return JSONResponse(
        status_code=429,
        content={
            "error": "too_many_requests",
            "message": "Muitas requisições. Aguarde alguns minutos e tente novamente.",
        }
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Require-2FA"],
)

# ====================
# EXCEPTION HANDLERS
# ====================

# Handler para erros de validação
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"❌ VALIDATION ERROR: {request.url}")
    logger.error(f"   Errors: {exc.errors()}")
    logger.error(f"   Body: {exc.body if hasattr(exc, 'body') else 'N/A'}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Dados inválidos",
            "details": exc.errors()
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Handler para erros HTTP (incluindo 401, 403, 404)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Não logar 404 de segmentação (comportamento esperado)
    if exc.status_code == 404 and "Segmento não encontrado" in str(exc.detail):
        pass  # Silencioso - é normal cliente não ter segmento calculado
    else:
        logger.warning(f"⚠️ HTTP {exc.status_code}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Handler para erros internos 500
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log estruturado de erro (ERROR)
    from app.utils.logger import logger as structured_logger
    from app.config import ENVIRONMENT

    structured_logger.error(
        event="unhandled_exception",
        message=f"Erro 500: {str(exc)}",
        path=request.url.path,
        method=request.method,
        exception_type=type(exc).__name__
    )
    logger.error(f"❌ Erro 500: {str(exc)}", exc_info=True)

    # Sanitização de erros em produção
    # Em produção: NÃO expor detalhes internos
    # Em dev/staging: Mostrar detalhes para debugging
    is_production = ENVIRONMENT.lower() in ["production", "prod"]

    if is_production:
        # Produção: Mensagem genérica (sem detalhes)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "Erro interno no servidor. Nossa equipe foi notificada.",
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    else:
        # Dev/Staging: Mostrar detalhes para debugging
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "Erro interno no servidor",
                "detail": str(exc),  # Apenas em dev
                "type": type(exc).__name__,  # Apenas em dev
            },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# ====================
# ARQUIVOS ESTÁTICOS - ANTES DOS ROUTERS!
# ====================

# Montar diretório de uploads como arquivos estáticos
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ====================
# REGISTRAR ROUTERS
# ====================

# Health & Readiness (Pré-Prod Block 2)
# - /health: Liveness probe (processo vivo?)
# - /ready: Readiness probe (app pronto para tráfego?)
# - Sem autenticação, sem tenant, sem prefixo
app.include_router(health_check_router, tags=["Infrastructure"])

app.include_router(auth_router, tags=["Autenticação Multi-Tenant"])
app.include_router(usuarios_router, tags=["Usuários & RBAC"])
app.include_router(roles_router, tags=["Roles & RBAC"])
app.include_router(permissions_router, tags=["Permissions & RBAC"])
app.include_router(clientes_router, tags=["Clientes & Pets"])
app.include_router(pets_router, tags=["Gestão de Pets"])  # Módulo dedicado separado
app.include_router(cadastros_router, tags=["Cadastros - Espécies & Raças"])  # Cadastros básicos
app.include_router(cliente_info_pdv_router, tags=["Clientes & Pets"])
app.include_router(importacao_router, prefix="/produtos", tags=["Importação de Produtos"])  # ANTES de produtos_router!
app.include_router(importacao_pessoas_router, tags=["Importação de Pessoas"])
app.include_router(produtos_router, tags=["Produtos"])
app.include_router(opcoes_racao_router, tags=["Opções de Ração"])
app.include_router(analise_racoes_router, tags=["Análises de Rações"])  # Fase 4: Dashboard de Análise
app.include_router(pdv_racoes_router, tags=["PDV - Rações Inteligentes"])  # Fase 5: Alertas e Sugestões
app.include_router(sugestoes_racoes_router, tags=["Sugestões Inteligentes - Rações"])  # Fase 6: Detecção e Otimização
app.include_router(ml_racoes_router, tags=["Machine Learning - Rações"])  # Fase 7: Aprendizado e Previsão
app.include_router(variacoes_router, tags=["Produtos - Variações"])  # Sprint 2
app.include_router(calculadora_racao_router, tags=["Calculadora de Ração"])
app.include_router(lembretes_router, tags=["Lembretes de Recorrência"])
app.include_router(relatorio_vendas_router, tags=["Relatório de Vendas"])  # ANTES de vendas_router!
app.include_router(vendas_router, tags=["Vendas & PDV"])
app.include_router(caixa_router, tags=["Controle de Caixa"])
app.include_router(nfe_router, tags=["Nota Fiscal Eletrônica (NF-e)"])
app.include_router(estoque_router, tags=["Gestão de Estoque"])
app.include_router(estoque_alertas_router, tags=["Estoque - Alertas Negativo"])
app.include_router(bling_sync_router, tags=["Sincronização Bling"])
app.include_router(pedidos_compra_router, tags=["Pedidos de Compra"])
app.include_router(notas_entrada_router, tags=["Notas de Entrada (XML)"])
app.include_router(contas_pagar_router, tags=["Financeiro - Contas a Pagar"])
app.include_router(contas_receber_router, tags=["Financeiro - Contas a Receber"])
app.include_router(conciliacao_cartao_router, tags=["Financeiro - Conciliação de Cartão"])
app.include_router(conciliacao_bancaria_router, tags=["Conciliação Bancária - OFX"])
app.include_router(stone_router, tags=["Stone - Pagamentos & Conciliação"])
app.include_router(conciliacao_router, tags=["Conciliação de Pagamentos"])
app.include_router(conciliacao_aba1_router, tags=["Conciliação Vendas - Aba 1 V2"])
app.include_router(conciliacao_historico_router, tags=["Conciliação - Histórico"])
app.include_router(admin_router, tags=["Administração"])
app.include_router(formas_pagamento_router, tags=["Formas de Pagamento & PDV"])
app.include_router(operadoras_router, tags=["Operadoras de Cartão"])
app.include_router(comissoes_router, tags=["Comissões"])
app.include_router(comissoes_demonstrativo_router, tags=["Comissões - Demonstrativo"])
app.include_router(comissoes_avancadas_router, tags=["Comissões - Avançadas"])
app.include_router(comissoes_diagnostico_router, tags=["Comissões - Diagnóstico"])
app.include_router(relatorios_comissoes_router, tags=["Comissões - Relatórios Analíticos"])
app.include_router(acertos_router, prefix="/acertos", tags=["Acertos Financeiros de Parceiros"])

app.include_router(dre_router, tags=["Financeiro - DRE"])
app.include_router(dre_canais_router, tags=["Financeiro - DRE por Canal"])
app.include_router(dre_plano_contas_router)
app.include_router(dre_classificacao_router, tags=["DRE - Classificação Automática"])
app.include_router(contas_bancarias_router, tags=["Financeiro - Contas Bancárias"])
app.include_router(financeiro_router, tags=["Financeiro - Configurações"])
app.include_router(lancamentos_router, tags=["Financeiro - Lançamentos"])
app.include_router(categorias_router, tags=["Financeiro - Categorias"])
app.include_router(bling_router, tags=["Integração Bling"])
app.include_router(bling_oauth_router, tags=["Bling OAuth"])
app.include_router(bling_pedido_router, tags=["Integração Bling - Pedido"])
app.include_router(bling_nf_router, tags=["Integração Bling - NF"])
app.include_router(dashboard_router, tags=["Dashboard Financeiro"])
app.include_router(ia_router, tags=["IA - Fluxo de Caixa"])
app.include_router(chat_router, tags=["IA - Chat Financeiro"])
app.include_router(dre_ia_router, tags=["IA - DRE Inteligente"])
app.include_router(extrato_ia_router, tags=["IA - Extrato Bancário (ABA 7)"])
app.include_router(ia_fluxo_router, tags=["IA - Fluxo Inteligente"])
app.include_router(analytics_router, tags=["Analytics - CQRS Read Models"])
app.include_router(audit_router, tags=["Auditoria (Read-Only)"])
app.include_router(tributacao_router, tags=["Tributação e Impostos"])
app.include_router(whatsapp_router, tags=["WhatsApp IA - Sprint 3"])  # ✅ REATIVADO Sprint 3
# app.include_router(whatsapp_router, tags=["WhatsApp CRM"])  # DESATIVADO - Usar novos endpoints WhatsApp IA
app.include_router(segmentacao_router, tags=["Segmentação de Clientes"])
app.include_router(pdv_ai_router, tags=["PDV - IA Contextual"])
app.include_router(pdv_internal_router, tags=["PDV - Internal API"])
app.include_router(racao_calculadora_internal_router, tags=["Calculadora de Ração - Internal API"])
app.include_router(fiscal_sugestao_router, tags=["Fiscal - Sugestões Inteligentes"])
app.include_router(produto_fiscal_router, tags=["Produto - Fiscal"])
app.include_router(pdv_fiscal_router, tags=["PDV - Fiscal em Tempo Real"])
app.include_router(produto_fiscal_v2_router, tags=["Produto - Fiscal V2"])
app.include_router(empresa_fiscal_router, tags=["Empresa - Configuração Fiscal"])
app.include_router(simples_router, tags=["Simples Nacional - Fechamento Mensal"])
app.include_router(auditoria_provisoes_router, tags=["Auditoria - Provisões"])
app.include_router(projecao_caixa_router, tags=["Projeção de Caixa - IA Determinística"])
app.include_router(simulacao_contratacao_router, tags=["Simulação de Contratação - IA Determinística"])
app.include_router(cargos_router, tags=["RH - Cargos"])
app.include_router(funcionarios_router, tags=["RH - Funcionários"])
app.include_router(empresa_config_router, tags=["Empresa - Configuração Geral"])
app.include_router(pdv_indicadores_router, tags=["PDV - Indicadores e Margens"])
app.include_router(empresa_router, tags=["Empresa - Configurações"])
app.include_router(configuracoes_entrega_router, tags=["Configurações - Entregas"])
app.include_router(rotas_entrega_router, tags=["Entregas - Rotas"])
app.include_router(acertos_entrega_router, tags=["Entregas - Acertos Financeiros"])
app.include_router(configuracao_custo_moto_router, tags=["Custos - Moto da Loja"])
app.include_router(dashboard_entregas_router)  # ETAPA 11.1 - Dashboard Financeiro (tags no router)
app.include_router(pendencia_estoque_router, tags=["Pendências de Estoque - Lista de Espera"])

# ============================================================================
# WHATSAPP + IA - SPRINT 2 & 4 & 5 & 6 & 7
# ============================================================================
app.include_router(whatsapp_webhook_router)  # Webhooks 360dialog (sem auth)
app.include_router(whatsapp_config_router)   # Configuração (com auth)
app.include_router(whatsapp_handoff_router)  # Sprint 4: Human Handoff (com auth)
app.include_router(whatsapp_websocket_router)  # Sprint 5: WebSocket Real-time
app.include_router(whatsapp_api_router)  # Sprint 6: Tools & Tests (com auth)
app.include_router(whatsapp_analytics_router)  # Sprint 7: Analytics & Reports (com auth)
app.include_router(whatsapp_security_router)  # Sprint 8: Security & LGPD (com auth)
app.include_router(health_router)  # Sprint 9: Health & Monitoring (sem auth)
app.include_router(admin_fix_router)  # Correções administrativas

# ============================================================================
# E-COMMERCE - Loja Pública
# ============================================================================
app.include_router(ecommerce_router)
app.include_router(ecommerce_auth_router)
app.include_router(ecommerce_entregador_router)
app.include_router(ecommerce_public_router)
app.include_router(ecommerce_cart_router)
app.include_router(ecommerce_checkout_router)
app.include_router(ecommerce_webhooks_router)
app.include_router(ecommerce_aparencia_router)
app.include_router(ecommerce_config_router)
app.include_router(ecommerce_notify_router)
app.include_router(ecommerce_analytics_router)
app.include_router(app_mobile_router)  # App Mobile - Rotas dos clientes
app.include_router(campaigns_router)   # Motor de Campanhas

# [DESATIVADO - PHASE 5] app.include_router(opportunity_metrics_router, tags=["PDV - Métricas de Oportunidades"])
# ❌ REMOVIDO: Routers duplicados (usuarios_router, roles_router, permissions_router já registrados na linha 316-318)

# ====================
# VALIDADOR DE AMBIENTE
# ====================

def validate_environment():
    """
    Valida configurações críticas antes do startup.

    NOVO (Pré-Prod Block 1):
    - Usa validate_settings() do módulo settings_validation
    - Validações rigorosas de ENV, DATABASE_URL, SQL_AUDIT_*
    - Validações específicas por ambiente (DEV/TEST/PROD)
    - Falha imediatamente se algo estiver incorreto
    """

    # ============================================================================
    # 1️⃣ VALIDAÇÃO COMPLETA DE SETTINGS (Pré-Prod Block 1)
    # ============================================================================

    try:
        validate_settings(settings)
        logger.info("✅ [PRÉ-PROD] Validação de settings concluída com sucesso")
    except Exception as e:
        # A exceção já foi logada pelo validate_settings
        # Apenas re-levanta para impedir inicialização
        raise

    # ============================================================================
    # 2️⃣ VALIDAÇÕES ADICIONAIS LEGACY (compatibilidade)
    # ============================================================================

    errors = []

    # Validação rigorosa de JWT_SECRET_KEY (mantida para compatibilidade)
    if JWT_SECRET_KEY in ["CHANGE_ME_IN_ENV", "CHANGE_ME", "change-this-to-a-random-secure-key"]:
        errors.append("JWT_SECRET_KEY must be changed from default value")
    elif len(JWT_SECRET_KEY) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters long")

    if errors:
        logger.error("[ERROR] ENVIRONMENT VALIDATION FAILED (LEGACY CHECKS)")
        for err in errors:
            logger.error(f" - {err}")
        raise RuntimeError("Invalid environment configuration")

    # Warnings (não bloqueiam inicialização)
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("[WARNING] GOOGLE_MAPS_API_KEY not set (features may be limited)")

# ====================
# EVENTOS
# ====================

@app.on_event("startup")
def on_startup():
    """
    Inicialização do sistema.

    Ordem de validações (Pré-Prod):
    1. Validação de ambiente (Bloco 1)
    2. Validação de migrations (Bloco 3)
    3. Inicialização de serviços
    """

    # ============================================================================
    # 1️⃣ PRÉ-PROD BLOCO 1: Validação de Ambiente
    # ============================================================================
    validate_environment()
    logger.info("\n" + "="*60)
    print_config()
    logger.info("="*60 + "\n")

    # ============================================================================
    # 2️⃣ PRÉ-PROD BLOCO 3: Validação de Migrations
    # ============================================================================
    # TEMPORARIAMENTE DESABILITADO PARA DESENVOLVIMENTO
    # try:
    #     # Usar engine do db module
    #     from app.db import engine
    #     ensure_db_ready(engine)
    #     logger.info("✅ [PRÉ-PROD] Database migrations check passed")
    # except Exception as e:
    #     logger.error(f"❌ [PRÉ-PROD] Database migrations check failed: {str(e)}")
    #     raise  # Bloqueia inicialização

    # ============================================================================
    # 3️⃣ Inicialização de Serviços
    # ============================================================================

    # Inicializar banco de dados
    # db.init_db()  # REMOVIDO: schema gerenciado por Alembic

    # Iniciar scheduler de acertos
    # TEMPORARIAMENTE DESABILITADO PARA DEBUG
    # try:
    #     from app.schedulers.acerto_scheduler import acerto_scheduler
    #     acerto_scheduler.start()
    #     logger.info("[OK] Scheduler de acertos iniciado!")
    # except Exception as e:
    #     logger.error(f"[ERROR] Erro ao iniciar scheduler de acertos: {str(e)}")

    # Iniciar scheduler de campanhas
    try:
        from app.campaigns.scheduler import CampaignScheduler
        global _campaign_scheduler
        _campaign_scheduler = CampaignScheduler()
        _campaign_scheduler.start()
        logger.info("[OK] Campaign Scheduler iniciado!")
    except Exception as e:
        logger.error(f"[ERROR] Erro ao iniciar Campaign Scheduler: {str(e)}")

    # Iniciar renovação automática de token Bling (a cada 5h)
    global _bling_token_thread
    _bling_token_stop_event.clear()
    _bling_token_thread = threading.Thread(
        target=_loop_renovacao_token_bling,
        name="bling-token-renovacao",
        daemon=True,
    )
    _bling_token_thread.start()

    # Iniciar job de expiração de reservas de pedidos vencidos (a cada 30min)
    global _expirar_reservas_thread
    _expirar_reservas_stop_event.clear()
    _expirar_reservas_thread = threading.Thread(
        target=_loop_expirar_reservas,
        name="expirar-reservas",
        daemon=True,
    )
    _expirar_reservas_thread.start()

    logger.info(f"[OK] {SYSTEM_NAME} v{SYSTEM_VERSION} iniciado!")
    logger.info("[API] Disponivel em: http://127.0.0.1:8000")
    logger.info("[DOCS] Documentacao em: http://127.0.0.1:8000/docs")


@app.on_event("shutdown")
def on_shutdown():
    """Finalização do sistema"""
    # Parar scheduler
    # TEMPORARIAMENTE DESABILITADO PARA DEBUG
    # try:
    #     from app.schedulers.acerto_scheduler import acerto_scheduler
    #     acerto_scheduler.shutdown()
    #     logger.info("[STOP] Scheduler de acertos parado!")
    # except Exception as e:
    #     logger.error(f"[ERROR] Erro ao parar scheduler: {str(e)}")

    # Parar scheduler de campanhas
    try:
        global _campaign_scheduler
        if _campaign_scheduler:
            _campaign_scheduler.shutdown()
            logger.info("[STOP] Campaign Scheduler parado!")
    except Exception as e:
        logger.error(f"[ERROR] Erro ao parar Campaign Scheduler: {str(e)}")

    global _bling_token_thread
    _bling_token_stop_event.set()
    if _bling_token_thread and _bling_token_thread.is_alive():
        _bling_token_thread.join(timeout=2)
    _bling_token_thread = None

    global _expirar_reservas_thread
    _expirar_reservas_stop_event.set()
    if _expirar_reservas_thread and _expirar_reservas_thread.is_alive():
        _expirar_reservas_thread.join(timeout=2)
    _expirar_reservas_thread = None

    logger.info("[STOP] Sistema encerrado")


# ====================
# ROTAS BÁSICAS
# ====================

@app.get("/")
def root():
    """Rota raiz"""
    return {
        "system": SYSTEM_NAME,
        "version": SYSTEM_VERSION,
        "status": "online",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check para monitoramento"""
    return {
        "status": "healthy",
        "system": SYSTEM_NAME,
        "version": SYSTEM_VERSION
    }


@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check - verifica se o sistema está pronto para receber requests
    Valida conexão com banco de dados
    """
    try:
        # Testar conexão com banco
        db.execute("SELECT 1")
        return {
            "status": "ready",
            "system": SYSTEM_NAME,
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "error": str(e)
            }
        )


@app.get("/test-racas")
def test_racas(especie: str = ""):
    """Rota de teste para debug"""
    return [
        {"id": 1, "nome": "Labrador", "especie": "Cão"},
        {"id": 2, "nome": "Golden Retriever", "especie": "Cão"},
        {"id": 3, "nome": "Siamês", "especie": "Gato"}
    ]


@app.get("/racas")
def get_racas(especie: Optional[str] = None):
    """
    Endpoint de raças para formulário de pets
    Retorna lista de raças filtradas por espécie
    """
    racas_cao = [
        {"id": 1, "nome": "Labrador", "especie": "Cão"},
        {"id": 2, "nome": "Golden Retriever", "especie": "Cão"},
        {"id": 3, "nome": "Bulldog", "especie": "Cão"},
        {"id": 4, "nome": "Poodle", "especie": "Cão"},
        {"id": 5, "nome": "Pastor Alemão", "especie": "Cão"},
        {"id": 6, "nome": "Beagle", "especie": "Cão"},
        {"id": 7, "nome": "Yorkshire", "especie": "Cão"},
        {"id": 8, "nome": "Shih Tzu", "especie": "Cão"},
        {"id": 9, "nome": "Pit Bull", "especie": "Cão"},
        {"id": 10, "nome": "Chihuahua", "especie": "Cão"},
        {"id": 11, "nome": "SRD (Sem Raça Definida)", "especie": "Cão"},
    ]

    racas_gato = [
        {"id": 12, "nome": "Siamês", "especie": "Gato"},
        {"id": 13, "nome": "Persa", "especie": "Gato"},
        {"id": 14, "nome": "Maine Coon", "especie": "Gato"},
        {"id": 15, "nome": "Bengal", "especie": "Gato"},
        {"id": 16, "nome": "Sphynx", "especie": "Gato"},
        {"id": 17, "nome": "Ragdoll", "especie": "Gato"},
        {"id": 18, "nome": "SRD (Sem Raça Definida)", "especie": "Gato"},
    ]

    if especie == "Cão":
        return racas_cao
    elif especie == "Gato":
        return racas_gato
    else:
        return racas_cao + racas_gato
