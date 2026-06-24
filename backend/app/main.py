"""
CorePet - Backend API
FastAPI + SQLAlchemy + SQLite/PostgreSQL
"""

import app.database.orm_guards  # ORM Guards: forca IDs=None antes do flush

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import SYSTEM_NAME, SYSTEM_VERSION, settings
from app.main_basic_routes import register_basic_routes
from app.main_http import (
    configure_middlewares,
    register_exception_handlers,
    register_proxy_headers_middleware,
)
from app.main_lifecycle import on_shutdown, on_startup
from app.utils.logger import configure_logging

# Importar modelos para registrar no SQLAlchemy (IMPORTANTE: antes de criar o app)
import app.pedido_models  # noqa: F401 - modelo base ecommerce
import app.veterinario_models  # noqa: F401 — garante registro no SQLAlchemy
import app.banho_tosa_models  # noqa: F401 - garante registro no SQLAlchemy
import app.models  # noqa: F401 - modelos principais
import app.template_models  # noqa: F401 - templates globais e auditoria de onboarding
import app.produtos_models  # noqa: F401 - modelo de lembretes e produtos
import app.idempotency_models  # noqa: F401 - modelo de idempotência
import app.models_configuracao_custo_moto  # noqa: F401 - custos da moto
import app.pendencia_estoque_models  # noqa: F401 - lista de espera
import app.ia.aba7_extrato_models  # noqa: F401 - modelos IA/DRE
import app.ia.aba7_models  # noqa: F401 - modelos DRE

# WHATSAPP + IA - NOVOS MODELOS (Sprint 2)
import app.whatsapp.models  # noqa: F401 - modelos WhatsApp IA
import app.whatsapp.models_handoff  # noqa: F401 - modelos handoff

DEBUG = settings.DEBUG

configure_logging()  # Configura formato estruturado para producao

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAR SISTEMA DE EVENTOS DE DOMINIO
# ============================================================================

try:
    from app.domain.events.setup import setup_event_handlers
    from app.db import get_session

    setup_event_handlers(db_session_factory=get_session)
    logger.info("[OK] Sistema de eventos de dominio configurado")

except Exception as e:
    logger.warning(f"[WARN] Nao foi possivel configurar sistema de eventos: {str(e)}")

# ============================================================================
# RATE LIMITER E FASTAPI APP
# ============================================================================

limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])

app = FastAPI(
    title=SYSTEM_NAME,
    description="Sistema completo de gestão para Pet Shop",
    version=SYSTEM_VERSION,
)

register_proxy_headers_middleware(app)
configure_middlewares(app, limiter)
register_exception_handlers(app)

# ============================================================================
# ARQUIVOS ESTATICOS - ANTES DOS ROUTERS!
# ============================================================================

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ============================================================================
# REGISTRAR ROUTERS
# ============================================================================

from app.main_routers import register_routers  # noqa: E402

register_routers(app)

# ============================================================================
# EVENTOS
# ============================================================================

app.add_event_handler("startup", on_startup)
app.add_event_handler("shutdown", on_shutdown)

# ============================================================================
# ROTAS BASICAS
# ============================================================================

register_basic_routes(app)
