"""Partes das rotas de formas de pagamento."""

from .analise_routes import router as analise_router
from .impostos_routes import router as impostos_router
from .taxas_routes import router as taxas_router

__all__ = ["analise_router", "impostos_router", "taxas_router"]
