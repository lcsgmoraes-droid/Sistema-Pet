"""Agregador das rotas de formas de pagamento, taxas e analise de venda."""

# ruff: noqa: F401

from fastapi import APIRouter

from .formas_pagamento_routes_parts import analise_router, impostos_router, taxas_router
from .formas_pagamento_routes_parts.analise_routes import analisar_venda
from .formas_pagamento_routes_parts.impostos_routes import (
    criar_imposto,
    definir_imposto_padrao,
    listar_impostos,
)
from .formas_pagamento_routes_parts.schemas import (
    AlertaAnalise,
    AnaliseVendaRequest,
    AnaliseVendaResponse,
    DetalhamentoComissao,
    FormaPagamentoAnalise,
    FormaPagamentoTaxaCreate,
    FormaPagamentoTaxaResponse,
    ItemAnaliseVenda,
)
from .formas_pagamento_routes_parts.taxas_routes import (
    atualizar_taxa,
    criar_taxa,
    deletar_taxa,
    listar_taxas,
)

router = APIRouter(prefix="/formas-pagamento", tags=["Formas de Pagamento"])
router.include_router(taxas_router)
router.include_router(analise_router)
router.include_router(impostos_router)
