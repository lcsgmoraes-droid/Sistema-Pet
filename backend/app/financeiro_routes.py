# ARQUIVO CRITICO DE PRODUCAO
# Este modulo e o agregador publico das rotas financeiras.
# Mantenha imports legados e a ordem dos subrouters ao refatorar.

"""
Rotas financeiras.

As implementacoes ficam em app.financeiro.*_routes; este arquivo preserva os
contratos historicos de importacao e registra os subrouters sob /financeiro.
"""

# ruff: noqa: F401

from fastapi import APIRouter

from .financeiro.common import financeiro_erp_required
from .financeiro.config_routes import (
    CategoriaCreate,
    FormaPagamentoCreate,
    FormaPagamentoResponse,
    atualizar_categoria,
    atualizar_forma_pagamento,
    criar_categoria,
    criar_forma_pagamento,
    desativar_categoria,
    excluir_forma_pagamento,
    listar_categorias,
    listar_formas_pagamento,
    router as config_router,
)
from .financeiro.fluxo_caixa_periodos import _agrupar_por_periodo
from .financeiro.fluxo_caixa_routes import get_fluxo_caixa, router as fluxo_caixa_router
from .financeiro.fluxo_caixa_schemas import (
    FluxoCaixaMovimentacao,
    FluxoCaixaPeriodo,
    FluxoCaixaResponse,
)
from .financeiro.cliente_routes import (
    get_historico_financeiro_cliente,
    get_resumo_financeiro_cliente,
    router as cliente_router,
)
from .financeiro.imobilizado_routes import router as imobilizado_router

router = APIRouter(prefix="/financeiro", tags=["Financeiro - Configura??es"])
router.include_router(config_router)
router.include_router(fluxo_caixa_router)
router.include_router(cliente_router)
router.include_router(imobilizado_router)

__all__ = [
    "CategoriaCreate",
    "FluxoCaixaMovimentacao",
    "FluxoCaixaPeriodo",
    "FluxoCaixaResponse",
    "FormaPagamentoCreate",
    "FormaPagamentoResponse",
    "_agrupar_por_periodo",
    "atualizar_categoria",
    "atualizar_forma_pagamento",
    "criar_categoria",
    "criar_forma_pagamento",
    "desativar_categoria",
    "excluir_forma_pagamento",
    "financeiro_erp_required",
    "get_fluxo_caixa",
    "get_historico_financeiro_cliente",
    "get_resumo_financeiro_cliente",
    "listar_categorias",
    "listar_formas_pagamento",
    "router",
]
