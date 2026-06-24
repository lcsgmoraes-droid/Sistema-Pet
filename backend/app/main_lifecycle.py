"""Application startup and shutdown hooks."""

import logging

from app.config import (
    GOOGLE_MAPS_API_KEY,
    JWT_SECRET_KEY,
    SYSTEM_NAME,
    SYSTEM_VERSION,
    print_config,
    settings,
)
from app.core.settings_validation import validate_settings
from app.db.migration_check import ensure_db_ready
from app.main_background_jobs import start_background_jobs, stop_background_jobs

logger = logging.getLogger(__name__)


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
    except Exception:
        # A exceção já foi logada pelo validate_settings
        # Apenas re-levanta para impedir inicialização
        raise

    # ============================================================================
    # 2️⃣ VALIDAÇÕES ADICIONAIS LEGACY (compatibilidade)
    # ============================================================================

    errors = []

    # Validação rigorosa de JWT_SECRET_KEY (mantida para compatibilidade)
    if JWT_SECRET_KEY in [
        "CHANGE_ME_IN_ENV",
        "CHANGE_ME",
        "change-this-to-a-random-secure-key",
    ]:
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
        logger.warning(
            "[WARNING] GOOGLE_MAPS_API_KEY not set (features may be limited)"
        )



def on_startup() -> None:
    """Inicializacao do sistema."""
    validate_environment()
    logger.info("\n" + "=" * 60)
    print_config()
    logger.info("=" * 60 + "\n")

    try:
        from app.db import engine

        ensure_db_ready(engine)
        logger.info("[PRÉ-PROD] Database migrations check passed")
    except Exception as e:
        logger.error(f"[PRÉ-PROD] Database migrations check failed: {str(e)}")
        raise

    start_background_jobs()

    logger.info(f"[OK] {SYSTEM_NAME} v{SYSTEM_VERSION} iniciado!")
    logger.info("[API] Disponivel em: http://127.0.0.1:8000")
    logger.info("[DOCS] Documentacao em: http://127.0.0.1:8000/docs")


def on_shutdown() -> None:
    """Finalizacao do sistema."""
    stop_background_jobs()
    logger.info("[STOP] Sistema encerrado")
