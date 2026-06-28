# -*- coding: utf-8 -*-
"""Agregador das rotas de analise avancada de racoes."""

# ruff: noqa: F401

from fastapi import APIRouter

from .analise_racoes_routes_parts import (
    filtros_router,
    produtos_router,
    resumo_router,
    segmentos_router,
)
from .analise_racoes_routes_parts.filtros_routes import obter_opcoes_filtros
from .analise_racoes_routes_parts.produtos_routes import (
    obter_produtos_para_comparacao,
)
from .analise_racoes_routes_parts.resumo_routes import obter_resumo_dashboard
from .analise_racoes_routes_parts.segmentos_routes import (
    analisar_margem_por_segmento,
    comparar_marcas,
    obter_ranking_vendas,
)

router = APIRouter(prefix="/racoes/analises", tags=["Analises Racoes"])
router.include_router(resumo_router)
router.include_router(segmentos_router)
router.include_router(filtros_router)
router.include_router(produtos_router)
