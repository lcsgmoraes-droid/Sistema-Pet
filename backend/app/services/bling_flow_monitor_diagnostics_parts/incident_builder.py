from __future__ import annotations

from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_flow_monitor_diagnostics_parts.context import _ultima_nf
from app.services.bling_flow_monitor_utils import (
    _dict,
    _json_safe,
    _nf_bling_id_valido,
    _primeiro_preenchido,
    _text,
)


def _make_incident(
    code: str,
    *,
    severity: str,
    title: str,
    message: str,
    suggested_action: str,
    auto_fixable: bool,
    pedido: PedidoIntegrado,
    sku: str | None = None,
    nf_bling_id: str | None = None,
    details: dict | None = None,
) -> dict:
    detalhes = _dict(_json_safe(details or {}))
    nf_detectada = _dict(detalhes.get("nf_detectada"))
    nf_payload = _ultima_nf(_dict(getattr(pedido, "payload", None)))
    nf_numero = _text(
        _primeiro_preenchido(
            detalhes.get("nf_numero"),
            nf_detectada.get("numero"),
            nf_payload.get("numero"),
        )
    )
    if nf_numero:
        detalhes["nf_numero"] = nf_numero

    return {
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "suggested_action": suggested_action,
        "auto_fixable": auto_fixable,
        "pedido_integrado_id": pedido.id,
        "pedido_bling_id": _text(pedido.pedido_bling_id),
        "nf_bling_id": _nf_bling_id_valido(nf_bling_id),
        "sku": _text(sku),
        "details": detalhes,
    }
