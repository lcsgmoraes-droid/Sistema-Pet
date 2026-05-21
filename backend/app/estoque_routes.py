"""
Router legado de estoque.

As rotas foram extraidas para modulos dedicados para manter o arquivo historico
como ponto de compatibilidade durante a refatoracao.
"""

from fastapi import APIRouter


router = APIRouter(prefix="/estoque", tags=["Estoque"])
