"""
SPRINT 6 - PASSO 6: Endpoints de Conferencia Avancada e Pagamento Parcial.

Fachada compativel das rotas avancadas de comissoes. Os handlers foram
separados em `app.comissoes_avancadas` para manter este arquivo pequeno sem
alterar os caminhos publicos sob `/comissoes`.
"""

from fastapi import APIRouter

from app.comissoes_avancadas.common import StructuredLogger, logger, struct_logger
from app.comissoes_avancadas.conferencia_routes import (
    conferencia_com_filtros_avancados,
    router as conferencia_router,
)
from app.comissoes_avancadas.pagamento_routes import (
    fechar_com_pagamento_parcial,
    listar_formas_pagamento,
    router as pagamento_router,
)

router = APIRouter(prefix="/comissoes", tags=["comissoes-avancadas"])
router.include_router(conferencia_router)
router.include_router(pagamento_router)

__all__ = [
    "StructuredLogger",
    "conferencia_com_filtros_avancados",
    "fechar_com_pagamento_parcial",
    "listar_formas_pagamento",
    "logger",
    "router",
    "struct_logger",
]
