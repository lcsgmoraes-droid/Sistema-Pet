"""
Router legado para movimentacoes manuais de estoque.

Entrada e saida manuais foram extraidas para routers dedicados.
"""

from fastapi import APIRouter


router = APIRouter(prefix="/estoque", tags=["Estoque"])
