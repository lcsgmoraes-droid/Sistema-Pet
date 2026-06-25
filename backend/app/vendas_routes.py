# -*- coding: utf-8 -*-
# ARQUIVO CRITICO DE PRODUCAO
# Este modulo e o agregador publico das rotas de Vendas (PDV).
# Mantenha imports legados e ordem de include_router ao refatorar.

"""
Rotas da API para o modulo de Vendas (PDV).

As implementacoes ficam em app.vendas.*_routes; este arquivo preserva o
contrato historico de importacao e registra os subrouters sob /vendas.
"""

# ruff: noqa: F401

import logging

from fastapi import APIRouter

from .vendas.cancelamento_routes import (
    cancelar_venda,
    excluir_venda,
    router as cancelamento_router,
)
from .vendas.comissoes import (
    _contar_comissoes_venda,
    _gerar_comissoes_pendentes_venda,
    _listar_pagamentos_venda_para_comissao,
    _parcelas_com_comissao_funcionario,
    _remover_comissoes_venda,
    _total_pago_venda,
)
from .vendas.crud_routes import (
    atualizar_venda,
    buscar_venda,
    criar_venda,
    listar_vendas,
    router as crud_router,
)
from .vendas.devolucoes_routes import registrar_devolucao, router as devolucoes_router
from .vendas.entrega_routes import (
    _resolver_retirado_por_conclusao,
    marcar_venda_entregue,
    marcar_venda_pronta_retirada,
    router as entrega_router,
)
from .vendas.finalizacao_routes import finalizar_venda, router as finalizacao_router
from .vendas.pagamentos_routes import (
    atualizar_nsu_pagamento,
    excluir_pagamento,
    listar_pagamentos_venda,
    router as pagamentos_router,
)
from .vendas.regras import _resolver_status_entrega_atualizacao, calcular_totais_venda
from .vendas.relatorios_routes import relatorio_resumo, router as relatorios_router
from .vendas.routes_common import (
    _normalizar_motivo_exclusao_venda,
    _obter_cliente_ou_404,
    _obter_venda_ou_404,
    _remover_provisoes_comissao_venda,
    _validar_tenant_e_obter_usuario,
)
from .vendas.schemas import (
    CancelarVendaRequest,
    CriarVendaRequest,
    ExcluirVendaRequest,
    FinalizarVendaRequest,
    MarcarEntregueRequest,
    VendaItemSchema,
    VendaPagamentoSchema,
)
from .vendas.status_routes import (
    atualizar_status_venda,
    reabrir_venda,
    router as status_router,
)

router = APIRouter(tags=["vendas"])
router.include_router(pagamentos_router, prefix="/vendas")
router.include_router(devolucoes_router, prefix="/vendas")
router.include_router(crud_router, prefix="/vendas")
router.include_router(entrega_router, prefix="/vendas")
router.include_router(finalizacao_router, prefix="/vendas")
router.include_router(cancelamento_router, prefix="/vendas")
router.include_router(status_router, prefix="/vendas")
router.include_router(relatorios_router, prefix="/vendas")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
