"""Fachada das rotas de DRE."""

from fastapi import APIRouter

from .dre_base_routes import (
    gerar_dre,
    gerar_dre_detalhado,
    router as base_router,
)
from .dre_calculos import (
    calcular_cmv,
    calcular_frete_notas_entrada,
    calcular_taxas_cartao,
    obter_despesas_por_categoria,
)
from .dre_export_routes import (
    exportar_dre_excel,
    exportar_dre_pdf,
    router as export_router,
)
from .dre_schemas import DREDetalhado, DREResponse

router = APIRouter()
router.include_router(base_router)
router.include_router(export_router)

__all__ = [
    "DREDetalhado",
    "DREResponse",
    "calcular_cmv",
    "calcular_frete_notas_entrada",
    "calcular_taxas_cartao",
    "exportar_dre_excel",
    "exportar_dre_pdf",
    "gerar_dre",
    "gerar_dre_detalhado",
    "obter_despesas_por_categoria",
    "router",
]
