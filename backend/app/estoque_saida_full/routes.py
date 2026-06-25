"""Agregador das rotas de baixa FULL por NF."""

from fastapi import APIRouter

from .nf_routes import router as nf_router
from .parser_routes import router as parser_router


router = APIRouter(prefix="/estoque", tags=["Estoque - Saida FULL"])
router.include_router(nf_router)
router.include_router(parser_router)
