"""Fachada das rotas de pendencias de compras."""

from fastapi import APIRouter

from .compras_pendencias_constants import (
    PENDENCIA_STATUS_ABERTA,
    PENDENCIA_STATUS_AGUARDANDO,
    PENDENCIA_STATUS_CANCELADA,
    PENDENCIA_STATUS_FINAIS,
    PENDENCIA_STATUS_RESOLVIDA,
    PENDENCIA_STATUS_TRATATIVA,
    PENDENCIA_STATUS_VALIDOS,
    UNIT_PRECISION,
)
from .compras_pendencias_consulta_routes import (
    atualizar_pendencia,
    listar_pendencias,
    obter_pendencia,
    router as consulta_router,
    status_envio_pendencias,
)
from .compras_pendencias_criacao_routes import (
    criar_pendencia_por_nota,
    router as criacao_router,
)
from .compras_pendencias_email_routes import (
    baixar_pdf_pendencia,
    enviar_email_pendencia,
    obter_email_pendencia,
    registrar_email_pendencia,
    router as email_router,
)
from .compras_pendencias_schemas import (
    AtualizarPendenciaPayload,
    CriarPendenciaNotaPayload,
    RegistrarEmailPayload,
)

router = APIRouter(prefix="/compras-pendencias", tags=["Compras - Pendencias"])
router.include_router(consulta_router)
router.include_router(criacao_router)
router.include_router(email_router)

__all__ = [
    "AtualizarPendenciaPayload",
    "CriarPendenciaNotaPayload",
    "PENDENCIA_STATUS_ABERTA",
    "PENDENCIA_STATUS_AGUARDANDO",
    "PENDENCIA_STATUS_CANCELADA",
    "PENDENCIA_STATUS_FINAIS",
    "PENDENCIA_STATUS_RESOLVIDA",
    "PENDENCIA_STATUS_TRATATIVA",
    "PENDENCIA_STATUS_VALIDOS",
    "RegistrarEmailPayload",
    "UNIT_PRECISION",
    "atualizar_pendencia",
    "baixar_pdf_pendencia",
    "criar_pendencia_por_nota",
    "enviar_email_pendencia",
    "listar_pendencias",
    "obter_email_pendencia",
    "obter_pendencia",
    "registrar_email_pendencia",
    "router",
    "status_envio_pendencias",
]
