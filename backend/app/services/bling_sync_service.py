"""Servico central de sincronizacao de estoque com o Bling.

Este modulo preserva o ponto de import legado e delega as responsabilidades para
mixins menores por fluxo operacional.
"""

from __future__ import annotations

from app.db import SessionLocal
from app.utils.tenant_safe_sql import execute_tenant_safe_all, execute_tenant_safe_one

from .bling_sync_auto_link import BlingSyncAutoLinkMixin
from .bling_sync_queue import BlingSyncQueueMixin
from .bling_sync_reprocess import BlingSyncReprocessMixin
from .bling_sync_reconciliation import BlingSyncReconciliationMixin
from .bling_sync_shared import (
    BLING_RATE_LIMIT_COOLDOWN_SECONDS,
    BLING_RATE_LIMIT_STATE_FILE,
    BLING_REPROCESS_IMMEDIATE_LIMIT,
    BLING_SECONDARY_READY_DEFER_THRESHOLD,
    BLING_SECONDARY_TOTAL_DEFER_THRESHOLD,
    BLING_STOCK_MIN_INTERVAL_SECONDS,
    DIVERGENCIA_MINIMA,
    MAX_RETRIES,
    RETRY_BACKOFF_MINUTES,
    _buscar_item_bling_para_produto,
    _cooldown_rate_limit_segundos,
    _detalhe_autenticacao_bling,
    _erro_autenticacao_bling,
    _erro_rate_limit_bling,
    _format_retry_eta,
    _latest_queue_ids_subquery,
    _mensagem_autenticacao_bling,
    _mensagem_rate_limit_bling,
    _normalizar_texto,
    _positive_limit,
    _registrar_cooldown_rate_limit,
    _remaining_limit,
    _secondary_jobs_defer_reason,
    _tenant_scope_or_current,
    listar_tenants_com_produto_bling_sync_ativo,
    listar_tenants_com_produto_bling_sync_recentes,
    listar_tenants_com_produtos_sem_vinculo_bling,
    utc_now,
)


class BlingSyncService(
    BlingSyncQueueMixin,
    BlingSyncReprocessMixin,
    BlingSyncReconciliationMixin,
    BlingSyncAutoLinkMixin,
):
    """Fachada compativel para fila, reconciliacao e auto-link Bling."""


__all__ = [
    "BlingSyncService",
    "DIVERGENCIA_MINIMA",
    "MAX_RETRIES",
    "RETRY_BACKOFF_MINUTES",
    "BLING_STOCK_MIN_INTERVAL_SECONDS",
    "BLING_RATE_LIMIT_COOLDOWN_SECONDS",
    "BLING_REPROCESS_IMMEDIATE_LIMIT",
    "BLING_SECONDARY_READY_DEFER_THRESHOLD",
    "BLING_SECONDARY_TOTAL_DEFER_THRESHOLD",
    "BLING_RATE_LIMIT_STATE_FILE",
    "SessionLocal",
    "execute_tenant_safe_all",
    "execute_tenant_safe_one",
    "_buscar_item_bling_para_produto",
    "_cooldown_rate_limit_segundos",
    "_detalhe_autenticacao_bling",
    "_erro_autenticacao_bling",
    "_erro_rate_limit_bling",
    "_format_retry_eta",
    "_latest_queue_ids_subquery",
    "_mensagem_autenticacao_bling",
    "_mensagem_rate_limit_bling",
    "_normalizar_texto",
    "_positive_limit",
    "_registrar_cooldown_rate_limit",
    "_remaining_limit",
    "_secondary_jobs_defer_reason",
    "_tenant_scope_or_current",
    "listar_tenants_com_produto_bling_sync_ativo",
    "listar_tenants_com_produto_bling_sync_recentes",
    "listar_tenants_com_produtos_sem_vinculo_bling",
    "utc_now",
]
