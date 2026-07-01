"""Fachada das rotas API para DRE Inteligente - ABA 7."""

from fastapi import APIRouter

from app.dre_ia_routes_parts import (
    AlocarDespesaRequest,
    CalcularDRECanalRequest,
    CalcularDREConsolidadoRequest,
    CalcularDREDetalhadadRequest,
    CalcularDRERequest,
    CategoriaRentabilidade,
    DRECompleto,
    DREDetalheResponse,
    DREResumo,
    InsightDRE,
    ProdutoRentabilidade,
    _usuario_dre,
    alocar_despesa,
    calcular_dre,
    calcular_dre_consolidado,
    calcular_dre_consolidado_canais,
    calcular_dre_detalhado,
    calcular_dre_por_canal,
    calcular_mes_atual,
    calcular_mes_passado,
    comparar_periodos,
    exportar_dre_excel,
    exportar_dre_pdf,
    listar_canais,
    listar_canais_disponiveis,
    listar_dres,
    listar_dres_por_canal,
    listar_setores,
    obter_anomalias_dre,
    obter_categorias_rentabilidade,
    obter_dre,
    obter_indices_mercado,
    obter_insights,
    obter_produtos_rentabilidade,
    recalcular_anomalias,
)
from app.dre_ia_routes_parts.anomalias_export_routes import (
    router as anomalias_export_router,
)
from app.dre_ia_routes_parts.base_routes import router as base_router
from app.dre_ia_routes_parts.canal_routes import router as canal_router
from app.dre_ia_routes_parts.detalhada_routes import router as detalhada_router

router = APIRouter(prefix="/ia/dre", tags=["IA - DRE Inteligente"])
router.include_router(base_router)
router.include_router(anomalias_export_router)
router.include_router(canal_router)
router.include_router(detalhada_router)

__all__ = [
    "_usuario_dre",
    "DREResumo",
    "DRECompleto",
    "ProdutoRentabilidade",
    "CategoriaRentabilidade",
    "InsightDRE",
    "CalcularDRERequest",
    "CalcularDRECanalRequest",
    "CalcularDREConsolidadoRequest",
    "CalcularDREDetalhadadRequest",
    "DREDetalheResponse",
    "AlocarDespesaRequest",
    "calcular_dre",
    "listar_canais",
    "listar_dres",
    "obter_dre",
    "obter_produtos_rentabilidade",
    "obter_categorias_rentabilidade",
    "obter_insights",
    "comparar_periodos",
    "obter_indices_mercado",
    "listar_setores",
    "calcular_mes_atual",
    "calcular_mes_passado",
    "obter_anomalias_dre",
    "recalcular_anomalias",
    "exportar_dre_pdf",
    "exportar_dre_excel",
    "listar_canais_disponiveis",
    "calcular_dre_por_canal",
    "calcular_dre_consolidado_canais",
    "listar_dres_por_canal",
    "calcular_dre_detalhado",
    "calcular_dre_consolidado",
    "alocar_despesa",
    "router",
]
