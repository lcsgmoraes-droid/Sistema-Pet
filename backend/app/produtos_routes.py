# ARQUIVO CRITICO DE PRODUCAO
# Este modulo e o agregador publico das rotas de Produtos.
# Mantenha imports legados e a ordem dos subrouters ao refatorar.

"""
Rotas para o modulo de Produtos.

As implementacoes ficam em app.produtos.*_routes; este arquivo preserva os
contratos historicos de importacao e registra os subrouters sob /produtos.
"""

# ruff: noqa: F401

import logging

from fastapi import APIRouter

from .produtos.atualizacao_lote_routes import (
    atualizar_produtos_lote,
    router as atualizacao_lote_router,
)
from .produtos.cadastro_routes import (
    atualizar_produto,
    criar_produto,
    obter_produto,
    router as cadastro_router,
)
from .produtos.catalogos_routes import router as catalogos_router
from .produtos.codigo_sku_routes import (
    gerar_codigo_barras,
    gerar_sku,
    router as codigo_sku_router,
    validar_codigo_barras,
)
from .produtos.core import (
    _aplicar_status_ativo_produto,
    _nome_indica_granel,
    _normalizar_filtro_ativo_produtos,
    _normalizar_payload_granel,
    _normalizar_promocao_erp_payload,
    _normalizar_sku_produto,
)
from .produtos.estado_routes import (
    atualizar_preco_produto,
    atualizar_status_ativo_produto,
    deletar_produto,
    router as estado_router,
)
from .produtos.fornecedores import (
    OPERACOES_FORNECEDOR_LOTE,
    _aplicar_fornecedor_produto_lote,
    _validar_fornecedor_produto_lote,
)
from .produtos.fornecedores_routes import router as fornecedores_router
from .produtos.historico_precos_routes import router as historico_precos_router
from .produtos.imagens_routes import router as imagens_router
from .produtos.listagem import (
    _aplicar_filtro_fornecedor_produto,
    _aplicar_filtros_basicos_produtos,
    _buscar_pagina_produtos_listagem,
    _enriquecer_produto_listagem,
    _expandir_produtos_listagem,
    _mapa_reservas_ativas_multitenant,
    _montar_query_listagem_produtos,
    _montar_query_produtos_vendaveis,
    _montar_resposta_produtos_paginados,
    _normalizar_paginacao_produtos,
    _resolver_fornecedor_ids_filtro_produto,
    _resolver_promocao_erp_produto,
)
from .produtos.listagem_routes import (
    listar_produtos,
    listar_produtos_vendaveis,
    router as listagem_router,
)
from .produtos.lotes_routes import (
    atualizar_lote,
    criar_lote,
    entrada_estoque,
    excluir_lote,
    listar_lotes,
    router as lotes_router,
    saida_estoque_fifo,
)
from .produtos.racao import _normalizar_classificacao_racao, _normalizar_payload_racao
from .produtos.racao_routes import router as racao_router
from .produtos.relatorios_routes import router as relatorios_router
from .produtos.schemas import (
    AtualizacaoLoteRequest,
    GerarCodigoBarrasRequest,
    GerarCodigoBarrasResponse,
    ProdutoAtivoUpdate,
    ProdutoCreate,
    ProdutoFusaoExecutarRequest,
    ProdutoFusaoPreviewRequest,
    ProdutoResponse,
    ProdutosPaginadosResponse,
    ProdutoUpdate,
)
from .produtos.validade import _mapa_validade_proxima_produtos
from .produtos.validators import (
    _obter_produto_ou_404,
    _validar_pode_inativar_produto,
    _validar_sku_unico,
    _validar_tenant_e_obter_usuario,
)
from .produtos.variacoes_fusao_routes import (
    excluir_variacao_permanentemente,
    executar_fusao_produtos_endpoint,
    listar_variacoes_excluidas,
    listar_variacoes_produto,
    preview_fusao_produtos,
    restaurar_variacao,
    router as variacoes_fusao_router,
)
from .produtos_models import Produto

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/produtos", tags=["produtos"])

router.include_router(catalogos_router)
router.include_router(fornecedores_router)
router.include_router(historico_precos_router)
router.include_router(imagens_router)
router.include_router(racao_router)
router.include_router(relatorios_router)
router.include_router(lotes_router)
router.include_router(codigo_sku_router)
router.include_router(listagem_router)
router.include_router(variacoes_fusao_router)
router.include_router(cadastro_router)
router.include_router(atualizacao_lote_router)
router.include_router(estado_router)

PRODUTO_SKU_COLUMN = getattr(Produto, "sku", None)

__all__ = [
    "atualizar_lote",
    "atualizar_preco_produto",
    "atualizar_produto",
    "atualizar_produtos_lote",
    "atualizar_status_ativo_produto",
    "criar_lote",
    "criar_produto",
    "deletar_produto",
    "entrada_estoque",
    "excluir_lote",
    "excluir_variacao_permanentemente",
    "gerar_codigo_barras",
    "gerar_sku",
    "listar_lotes",
    "listar_produtos",
    "listar_produtos_vendaveis",
    "listar_variacoes_excluidas",
    "listar_variacoes_produto",
    "obter_produto",
    "router",
    "saida_estoque_fifo",
    "validar_codigo_barras",
]
