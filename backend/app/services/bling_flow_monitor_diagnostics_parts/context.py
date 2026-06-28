from __future__ import annotations

from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_flow_monitor_utils import (
    _dict,
    _normalizar_contexto_nf,
    _primeiro_preenchido,
    _text,
)


NF_AUTHORIZED_CODES = {2, 5, 9}


def _ultima_nf(payload: dict | None) -> dict:
    payload = _dict(payload)
    pedido = _dict(payload.get("pedido"))
    for candidato in (
        payload.get("ultima_nf"),
        pedido.get("notaFiscal"),
        pedido.get("nota"),
        pedido.get("nfe"),
    ):
        nf = _normalizar_contexto_nf(candidato)
        if nf:
            return nf
    return {}


def _nf_autorizada(payload: dict | None) -> bool:
    nf = _ultima_nf(payload)
    return _nf_contexto_autorizado(nf)


def _nf_contexto_autorizado(nf: dict | None) -> bool:
    nf = _dict(nf)
    codigo = nf.get("situacao_codigo")
    try:
        if codigo is not None and int(codigo) in NF_AUTHORIZED_CODES:
            return True
    except (TypeError, ValueError):
        pass

    situacao = (nf.get("situacao") or nf.get("status") or "").strip().lower()
    return any(token in situacao for token in ("autoriz", "emitida", "emitido"))


def _numero_pedido_loja_pedido(pedido: PedidoIntegrado | None) -> str | None:
    payload = _dict(getattr(pedido, "payload", None))
    pedido_payload = _dict(payload.get("pedido"))
    webhook_payload = _dict(payload.get("webhook"))

    for candidato in (
        pedido_payload.get("numeroLoja"),
        pedido_payload.get("numeroPedidoLoja"),
        pedido_payload.get("numeroPedido"),
        webhook_payload.get("numeroLoja"),
        webhook_payload.get("numeroPedidoLoja"),
        payload.get("numeroLoja"),
        payload.get("numeroPedidoLoja"),
    ):
        texto = _text(candidato)
        if texto:
            return texto
    return None


def _loja_id_pedido_integrado(pedido: PedidoIntegrado | None) -> str | None:
    payload = _dict(getattr(pedido, "payload", None))
    pedido_payload = _dict(payload.get("pedido"))
    webhook_payload = _dict(payload.get("webhook"))
    pedido_loja = _dict(pedido_payload.get("loja"))
    webhook_loja = _dict(webhook_payload.get("loja"))
    loja_virtual = _dict(pedido_payload.get("lojaVirtual"))

    return _text(
        _primeiro_preenchido(
            pedido_loja.get("id"),
            webhook_loja.get("id"),
            loja_virtual.get("id"),
            pedido_payload.get("loja_id"),
            webhook_payload.get("loja_id"),
        )
    )


def _loja_id_nf_contexto(nf_contexto: dict | None) -> str | None:
    nf_contexto = _dict(nf_contexto)
    loja = _dict(nf_contexto.get("loja"))
    return _text(_primeiro_preenchido(nf_contexto.get("loja_id"), loja.get("id")))


def _canal_pedido_integrado(pedido: PedidoIntegrado | None) -> str | None:
    if not pedido:
        return None

    try:
        from app.integracao_bling_pedido_routes import _resolver_canal_pedido

        canal, _, _ = _resolver_canal_pedido(
            _dict(getattr(pedido, "payload", None)),
            getattr(pedido, "canal", None),
        )
        return _text(canal)
    except Exception:
        return _text(getattr(pedido, "canal", None))


def _canal_label_nf_contexto(data: dict | None) -> tuple[str | None, str | None]:
    data = _dict(data)
    if not data:
        return None, None

    try:
        from app.nfe_routes import _normalizar_resumo_canal

        resumo = _normalizar_resumo_canal(data)
        return _text(resumo.get("canal")), _text(resumo.get("canal_label"))
    except Exception:
        return None, None


def _pedido_total(pedido: PedidoIntegrado | None) -> float | None:
    payload = _dict(getattr(pedido, "payload", None))
    pedido_payload = _dict(payload.get("pedido"))
    financeiro = _dict(pedido_payload.get("financeiro"))
    ultima_nf = _ultima_nf(payload)

    for candidato in (
        ultima_nf.get("valor_total"),
        financeiro.get("total"),
        pedido_payload.get("total"),
        pedido_payload.get("valorTotal"),
        pedido_payload.get("valor_total"),
    ):
        try:
            valor = float(candidato)
            if valor > 0:
                return valor
        except (TypeError, ValueError):
            continue
    return None
