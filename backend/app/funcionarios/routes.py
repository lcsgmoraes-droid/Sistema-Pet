"""Agregador das rotas de funcionarios/RH."""

from fastapi import APIRouter

from .base_routes import router as base_router
from .eventos_routes import router as eventos_router

router = APIRouter(tags=["RH - Funcionários"])
router.include_router(base_router, prefix="/funcionarios")
router.include_router(eventos_router, prefix="/funcionarios")
