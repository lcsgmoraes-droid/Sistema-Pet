"""Agregador das rotas de internacao veterinaria."""

from fastapi import APIRouter

from .veterinario_internacao_routes_parts import (
    agenda_router,
    historico_router,
    listagem_config_router,
    mutacao_router,
)

router = APIRouter()
router.include_router(listagem_config_router)
router.include_router(agenda_router)
router.include_router(mutacao_router)
router.include_router(historico_router)
