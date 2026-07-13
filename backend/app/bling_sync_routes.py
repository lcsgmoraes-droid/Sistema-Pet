"""
SINCRONIZACAO BLING - CorePet
Sincronizacao bidirecional de estoque entre sistema e Bling.

Este modulo preserva o ponto de import legado e agrega subrouters menores por
fluxo operacional.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from .bling_sync.catalog_snapshots import (
    _get_resumo_cobertura_bling,
    _get_snapshot_faltantes_bling,
    _get_snapshot_sem_vinculo_com_match_bling,
    _invalidate_bling_snapshots,
    _remover_ids_do_snapshot_sem_vinculo_cache,
)
from .bling_sync.config_routes import (
    configurar_sincronizacao,
    router as config_router,
    vincular_produto_bling,
    vincular_produto_bling_automatico,
)
from .bling_sync.dashboard_routes import (
    criar_produto_local_para_faltante_bling,
    dashboard_pendencias_bling,
    health_sincronizacao,
    listar_faltantes_bling,
    listar_produtos_sem_vinculo,
    resumo_cobertura_bling,
    router as dashboard_router,
)
from .bling_sync.exportacao_produtos_routes import (
    exportar_produto_local_para_bling,
    exportar_produtos_locais_para_bling_lote,
    router as exportacao_produtos_bling_router,
)
from .bling_sync.operational_routes import (
    _executar_reconciliacao_geral_em_background,
    enviar_estoque_para_bling,
    forcar_sincronizacao_produto,
    reconciliar_estoque,
    reconciliar_geral,
    reconciliar_recentes,
    reprocessar_falhas,
    router as operational_router,
    status_reconciliar_geral,
    status_sincronizacao,
    status_sincronizacao_problemas,
)
from .bling_sync.product_matching import (
    _barcode_bling,
    _coerce_float,
    _escolher_item_melhor_match,
    _escolher_item_sku_estrito,
    _extrair_lista_produtos_bling,
    _limpar_texto_busca,
    _montar_codigos_busca,
    _montar_codigos_busca_estrita,
    _produto_eh_pai,
    _produto_sincroniza_estoque,
    _sku_bling,
    _texto_limpo,
    _tipo_produto_local,
)
from .bling_sync.produtos_routes import (
    importar_imagens_dos_produtos_bling as importar_imagens_dos_produtos_bling,
    listar_produtos_bling as listar_produtos_bling,
    router as produtos_bling_router,
)
from .bling_sync.routes_common import (
    PRODUTO_NAO_ENCONTRADO,
    _buscar_item_bling_com_retry,
    _buscar_item_bling_para_vinculo,
    _buscar_item_bling_por_codigos,
    _buscar_item_bling_por_codigos_com_retry,
    _buscar_produtos_bling_por_termo,
    _consultar_produto_bling_com_retry,
    _upsert_sync_vinculo,
    utc_now,
)
from .bling_sync.status_queries import _build_sync_problem_query
from .bling_sync.webhook_routes import (
    router as webhook_router,
    vincular_todos_por_sku,
    webhook_bling,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque/sync", tags=["Sincronizacao Bling"])
router.include_router(produtos_bling_router)
router.include_router(exportacao_produtos_bling_router)
router.include_router(config_router)
router.include_router(dashboard_router)
router.include_router(operational_router)
router.include_router(webhook_router)

logger.info("Modulo de sincronizacao Bling carregado")

__all__ = [
    "router",
    "PRODUTO_NAO_ENCONTRADO",
    "utc_now",
    "_buscar_item_bling_para_vinculo",
    "_buscar_item_bling_por_codigos",
    "_buscar_produtos_bling_por_termo",
    "_buscar_item_bling_com_retry",
    "_buscar_item_bling_por_codigos_com_retry",
    "_consultar_produto_bling_com_retry",
    "_upsert_sync_vinculo",
    "_executar_reconciliacao_geral_em_background",
    "configurar_sincronizacao",
    "vincular_produto_bling",
    "vincular_produto_bling_automatico",
    "health_sincronizacao",
    "listar_produtos_sem_vinculo",
    "resumo_cobertura_bling",
    "listar_faltantes_bling",
    "dashboard_pendencias_bling",
    "criar_produto_local_para_faltante_bling",
    "exportar_produto_local_para_bling",
    "exportar_produtos_locais_para_bling_lote",
    "enviar_estoque_para_bling",
    "forcar_sincronizacao_produto",
    "status_sincronizacao",
    "status_sincronizacao_problemas",
    "reprocessar_falhas",
    "reconciliar_recentes",
    "reconciliar_geral",
    "status_reconciliar_geral",
    "reconciliar_estoque",
    "webhook_bling",
    "vincular_todos_por_sku",
    "listar_produtos_bling",
    "importar_imagens_dos_produtos_bling",
    "_get_resumo_cobertura_bling",
    "_get_snapshot_faltantes_bling",
    "_get_snapshot_sem_vinculo_com_match_bling",
    "_invalidate_bling_snapshots",
    "_remover_ids_do_snapshot_sem_vinculo_cache",
    "_barcode_bling",
    "_coerce_float",
    "_escolher_item_melhor_match",
    "_escolher_item_sku_estrito",
    "_extrair_lista_produtos_bling",
    "_limpar_texto_busca",
    "_montar_codigos_busca",
    "_montar_codigos_busca_estrita",
    "_produto_eh_pai",
    "_produto_sincroniza_estoque",
    "_sku_bling",
    "_texto_limpo",
    "_tipo_produto_local",
    "_build_sync_problem_query",
]
