"""Helpers para reconciliar vinculos incorretos de NF e pedido Bling."""

import json

from sqlalchemy.orm import Session

from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao

from .common import _text


def _numero_nf_pedido(
    pedido: PedidoIntegrado | None, fallback_nf_id: str | None = None
) -> str | None:
    payload_bruto = getattr(pedido, "payload", None)
    payload = payload_bruto if isinstance(payload_bruto, dict) else {}
    pedido_payload = (
        payload.get("pedido") if isinstance(payload.get("pedido"), dict) else {}
    )
    ultima_nf = (
        payload.get("ultima_nf")
        or pedido_payload.get("notaFiscal")
        or pedido_payload.get("nota")
        or pedido_payload.get("nfe")
    )
    ultima_nf = ultima_nf if isinstance(ultima_nf, dict) else {}
    numero = str(ultima_nf.get("numero") or "").strip()
    return numero or None


def _nf_cache_pertence_a_outro_pedido(
    db: Session,
    *,
    tenant_id,
    nf_bling_id: str | None,
    pedido_bling_id_atual: str | None,
) -> str | None:
    nf_bling_id = _text(nf_bling_id)
    pedido_bling_id_atual = _text(pedido_bling_id_atual)
    if not nf_bling_id or not pedido_bling_id_atual:
        return None

    registro = (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            BlingNotaFiscalCache.bling_id == nf_bling_id,
        )
        .order_by(BlingNotaFiscalCache.id.desc())
        .first()
    )
    pedido_ref = _text(getattr(registro, "pedido_bling_id_ref", None))
    if pedido_ref and pedido_ref != pedido_bling_id_atual:
        return pedido_ref
    return None


def _restaurar_lotes_consumidos(db: Session, movimentacao: EstoqueMovimentacao) -> int:
    from app.produtos_models import ProdutoLote

    bruto = getattr(movimentacao, "lotes_consumidos", None)
    if not bruto:
        return 0
    try:
        lotes = json.loads(bruto) if isinstance(bruto, str) else bruto
    except Exception:
        lotes = []

    restaurados = 0
    for item_lote in lotes or []:
        lote_id = item_lote.get("lote_id")
        quantidade = float(item_lote.get("quantidade") or 0)
        if not lote_id or quantidade <= 0:
            continue

        lote = db.query(ProdutoLote).filter(ProdutoLote.id == lote_id).first()
        if not lote:
            continue

        lote.quantidade_disponivel = float(lote.quantidade_disponivel or 0) + quantidade
        if lote.quantidade_disponivel > 0:
            lote.status = "ativo"
        db.add(lote)
        restaurados += 1

    return restaurados


def _recarregar_pedido_e_itens_para_nf(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
) -> tuple[PedidoIntegrado, list[PedidoIntegradoItem]]:
    if not isinstance(db, Session):
        return pedido, list(itens or [])

    pedido_query = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.id == pedido.id,
        PedidoIntegrado.tenant_id == pedido.tenant_id,
    )
    if hasattr(pedido_query, "with_for_update"):
        pedido_query = pedido_query.with_for_update()
    pedido_lock = pedido_query.first() or pedido

    itens_query = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido_lock.id
    )
    if hasattr(itens_query, "with_for_update"):
        itens_query = itens_query.with_for_update()
    itens_lock = itens_query.all() or list(itens or [])

    return pedido_lock, itens_lock
