"""Partes das rotas de analise de racoes."""

from .filtros_routes import router as filtros_router
from .produtos_routes import router as produtos_router
from .resumo_routes import router as resumo_router
from .segmentos_routes import router as segmentos_router

__all__ = [
    "filtros_router",
    "produtos_router",
    "resumo_router",
    "segmentos_router",
]
