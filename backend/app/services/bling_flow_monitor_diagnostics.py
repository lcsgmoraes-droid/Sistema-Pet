from __future__ import annotations

from app.services.bling_flow_monitor_diagnostics_parts.context import (
    NF_AUTHORIZED_CODES,
    _canal_label_nf_contexto,
    _canal_pedido_integrado,
    _loja_id_nf_contexto,
    _loja_id_pedido_integrado,
    _nf_autorizada,
    _nf_contexto_autorizado,
    _numero_pedido_loja_pedido,
    _pedido_total,
    _ultima_nf,
)
from app.services.bling_flow_monitor_diagnostics_parts.incident_builder import (
    _make_incident,
)
from app.services.bling_flow_monitor_diagnostics_parts.inventory import (
    _contar_movimentacoes_saida_nf,
    _produto_por_sku,
)
from app.services.bling_flow_monitor_diagnostics_parts.pedido_diagnostics import (
    diagnosticar_pedido_integrado,
)
from app.services.bling_flow_monitor_diagnostics_parts.recent_nfs import (
    _NF_RECENTES_CACHE_SECONDS,
    _NF_RECENTES_ENRICH_DELAY_SECONDS,
    _NF_RECENTES_ENRICH_LIMIT,
    _enriquecer_resumo_nf_com_relacao,
    _indexar_nfs_por_pedido_loja,
    _nf_detectada_combina_com_pedido,
    _nf_recentes_cache,
    _obter_nfs_recentes_bling,
    _obter_nfs_recentes_cache_local,
    _resumir_nf_bling_recente,
)
from app.services.bling_flow_monitor_utils import (
    _coerce_int,
    _dict,
    _json_safe,
    _list,
    _nf_bling_id_valido,
    _normalizar_contexto_nf,
    _primeiro_preenchido,
    _text,
    _utcnow,
)

__all__ = [
    "NF_AUTHORIZED_CODES",
    "_NF_RECENTES_CACHE_SECONDS",
    "_NF_RECENTES_ENRICH_DELAY_SECONDS",
    "_NF_RECENTES_ENRICH_LIMIT",
    "_canal_label_nf_contexto",
    "_canal_pedido_integrado",
    "_coerce_int",
    "_contar_movimentacoes_saida_nf",
    "_dict",
    "_enriquecer_resumo_nf_com_relacao",
    "_indexar_nfs_por_pedido_loja",
    "_json_safe",
    "_list",
    "_loja_id_nf_contexto",
    "_loja_id_pedido_integrado",
    "_make_incident",
    "_nf_autorizada",
    "_nf_bling_id_valido",
    "_nf_contexto_autorizado",
    "_nf_detectada_combina_com_pedido",
    "_nf_recentes_cache",
    "_normalizar_contexto_nf",
    "_numero_pedido_loja_pedido",
    "_obter_nfs_recentes_bling",
    "_obter_nfs_recentes_cache_local",
    "_pedido_total",
    "_primeiro_preenchido",
    "_produto_por_sku",
    "_resumir_nf_bling_recente",
    "_text",
    "_ultima_nf",
    "_utcnow",
    "diagnosticar_pedido_integrado",
]
