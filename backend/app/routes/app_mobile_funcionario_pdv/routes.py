"""Agregador das rotas do PDV do funcionario."""

from fastapi import APIRouter

from .beneficios import router as beneficios_router
from .caixa import router as caixa_router
from .clientes import router as clientes_router
from .pagamentos import router as pagamentos_router
from .produtos import router as produtos_router
from .vendas import router as vendas_router

router = APIRouter()
router.include_router(produtos_router)
router.include_router(clientes_router)
router.include_router(caixa_router)
router.include_router(pagamentos_router)
router.include_router(beneficios_router)
router.include_router(vendas_router)
