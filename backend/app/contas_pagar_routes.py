"""Agregador das rotas de contas a pagar."""

from fastapi import APIRouter

from .financeiro.contas_pagar_common import (
    _decimal_monetario,
    _expressao_texto_busca,
    _normalizar_texto_busca,
    _obter_tipo_produto_revenda_id,
    _registrar_observacao_operacao_conta_pagar,
    _resolver_dre_subcategoria_conta_pagar,
    _valor_reais_para_centavos,
)
from .financeiro.contas_pagar_analise_routes import (
    analisar_contas_pagar_abertas,
    router as analise_router,
)
from .financeiro.contas_pagar_consulta_routes import (
    classificar_conta_pagar,
    listar_contas_pagar,
    router as consulta_router,
)
from .financeiro.contas_pagar_criacao_routes import (
    criar_conta_pagar,
    router as criacao_router,
)
from .financeiro.contas_pagar_manutencao_routes import (
    atualizar_conta_pagar,
    buscar_conta_pagar,
    cancelar_conta_pagar,
    estornar_pagamento_conta_pagar,
    excluir_conta_pagar,
    router as manutencao_router,
)
from .financeiro.contas_pagar_pagamento_routes import (
    dashboard_contas_pagar,
    registrar_pagamento,
    registrar_pagamento_lote,
    router as pagamento_router,
)
from .financeiro.contas_pagar_recorrencia_routes import (
    excluir_recorrencias_contas_pagar as excluir_recorrencias_contas_pagar,
    listar_recorrencia_conta_pagar as listar_recorrencia_conta_pagar,
    processar_recorrencias_contas_pagar as processar_recorrencias_contas_pagar,
    router as recorrencia_router,
)
from .financeiro.contas_pagar_schemas import (
    ContaPagarClassificacaoUpdate,
    ContaPagarCreate,
    ContaPagarOperacaoRequest,
    ContaPagarRecorrenciaBulkDelete as ContaPagarRecorrenciaBulkDelete,
    ContaPagarRecorrenciaItemResponse as ContaPagarRecorrenciaItemResponse,
    ContaPagarResponse,
    ContaPagarUpdate,
    PagamentoCreate,
    PagamentoLoteCreate,
)

router = APIRouter(prefix="/contas-pagar", tags=["Contas a Pagar"])
router.include_router(analise_router)
router.include_router(criacao_router)
router.include_router(consulta_router)
router.include_router(manutencao_router)
router.include_router(pagamento_router)
router.include_router(recorrencia_router)

__all__ = [
    "ContaPagarClassificacaoUpdate",
    "ContaPagarCreate",
    "ContaPagarOperacaoRequest",
    "ContaPagarRecorrenciaBulkDelete",
    "ContaPagarRecorrenciaItemResponse",
    "ContaPagarResponse",
    "ContaPagarUpdate",
    "PagamentoCreate",
    "PagamentoLoteCreate",
    "analisar_contas_pagar_abertas",
    "atualizar_conta_pagar",
    "buscar_conta_pagar",
    "cancelar_conta_pagar",
    "classificar_conta_pagar",
    "criar_conta_pagar",
    "dashboard_contas_pagar",
    "estornar_pagamento_conta_pagar",
    "excluir_conta_pagar",
    "excluir_recorrencias_contas_pagar",
    "listar_contas_pagar",
    "listar_recorrencia_conta_pagar",
    "processar_recorrencias_contas_pagar",
    "registrar_pagamento",
    "registrar_pagamento_lote",
    "router",
    "_decimal_monetario",
    "_expressao_texto_busca",
    "_normalizar_texto_busca",
    "_obter_tipo_produto_revenda_id",
    "_registrar_observacao_operacao_conta_pagar",
    "_resolver_dre_subcategoria_conta_pagar",
    "_valor_reais_para_centavos",
]
