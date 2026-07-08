"""Fachada das rotas de contas a receber."""

from fastapi import APIRouter

from .contas_receber_analise_routes import (
    analisar_contas_receber_abertas,
    router as analise_router,
)
from .contas_receber_consulta_routes import (
    buscar_conta_receber,
    dashboard_contas_receber,
    listar_contas_receber,
    router as consulta_router,
)
from .contas_receber_criacao_routes import (
    criar_conta_receber,
    router as criacao_router,
)
from .contas_receber_recebimentos_routes import (
    registrar_recebimento,
    router as recebimentos_router,
)
from .contas_receber_recorrencias import calcular_proxima_recorrencia
from .contas_receber_recorrencias_routes import (
    processar_recorrencias_contas_receber,
    router as recorrencias_router,
)
from .contas_receber_schemas import (
    ContaReceberCreate,
    ContaReceberResponse,
    RecebimentoCreate,
)

router = APIRouter(prefix="/contas-receber", tags=["Contas a Receber"])
router.include_router(criacao_router)
router.include_router(analise_router)
router.include_router(consulta_router)
router.include_router(recebimentos_router)
router.include_router(recorrencias_router)

__all__ = [
    "ContaReceberCreate",
    "ContaReceberResponse",
    "RecebimentoCreate",
    "analisar_contas_receber_abertas",
    "buscar_conta_receber",
    "calcular_proxima_recorrencia",
    "criar_conta_receber",
    "dashboard_contas_receber",
    "listar_contas_receber",
    "processar_recorrencias_contas_receber",
    "registrar_recebimento",
    "router",
]
