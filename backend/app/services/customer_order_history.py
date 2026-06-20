from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import joinedload

from app.idempotency_models import IdempotencyKey
from app.models import Cliente
from app.pedido_models import Pedido, PedidoItem
from app.services.sales_channel import normalize_sales_channel
from app.vendas_models import Venda, VendaItem


CHANNEL_LABELS = {
    "ecommerce": "Ecommerce",
    "app": "App mobile",
    "loja_fisica": "Loja fisica / ERP",
    "mercado_livre": "Mercado Livre",
    "shopee": "Shopee",
    "amazon": "Amazon",
}

ECOMMERCE_SALE_INTEGRATION_ENDPOINT = "POST /api/ecommerce/integracao/venda"
CHECKOUT_FINALIZAR_ENDPOINT = "POST /api/checkout/finalizar"


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else None


def channel_label_for(channel: Any) -> str:
    normalized = normalize_sales_channel(channel, default="ecommerce")
    if normalized in CHANNEL_LABELS:
        return CHANNEL_LABELS[normalized]
    return normalized.replace("_", " ").strip().capitalize() or "Ecommerce"


def _checkout_item_dict(item: Any) -> dict:
    return {
        "produto_id": getattr(item, "produto_id", None),
        "nome": getattr(item, "nome", None) or "Produto",
        "quantidade": _to_float(getattr(item, "quantidade", 0)),
        "preco_unitario": _to_float(getattr(item, "preco_unitario", 0)),
        "subtotal": _to_float(getattr(item, "subtotal", 0)),
    }


def _sale_item_dict(item: Any) -> dict:
    item_dict = item.to_dict() if hasattr(item, "to_dict") else {}
    produto = getattr(item, "produto", None)
    nome = (
        item_dict.get("produto_nome")
        or item_dict.get("servico_descricao")
        or getattr(item, "produto_nome", None)
        or getattr(item, "servico_descricao", None)
        or getattr(produto, "nome", None)
        or "Produto"
    )
    return {
        "produto_id": item_dict.get("produto_id", getattr(item, "produto_id", None)),
        "nome": nome,
        "quantidade": _to_float(
            item_dict.get("quantidade", getattr(item, "quantidade", 0))
        ),
        "preco_unitario": _to_float(
            item_dict.get("preco_unitario", getattr(item, "preco_unitario", 0))
        ),
        "subtotal": _to_float(item_dict.get("subtotal", getattr(item, "subtotal", 0))),
    }


def build_checkout_history_entry(
    pedido: Any,
    itens: list[Any],
    *,
    payment_info: dict | None = None,
    venda_info: dict | None = None,
) -> dict:
    payment_info = payment_info or {}
    venda_info = venda_info or {}
    canal = normalize_sales_channel(
        getattr(pedido, "origem", None) or venda_info.get("canal"),
        default="ecommerce",
    )
    pedido_id = getattr(pedido, "pedido_id", None)
    return {
        "historico_id": f"pedido:{pedido_id}",
        "origem_tipo": "pedido_online",
        "pedido_id": pedido_id,
        "venda_id": venda_info.get("venda_id"),
        "numero": pedido_id,
        "status": getattr(pedido, "status", None),
        "status_entrega": venda_info.get("status_entrega"),
        "retirado_por": venda_info.get("retirado_por"),
        "tem_entrega": venda_info.get("tem_entrega"),
        "tipo_retirada": getattr(pedido, "tipo_retirada", None),
        "is_drive": bool(getattr(pedido, "is_drive", False)),
        "drive_chegou_at": _to_iso(getattr(pedido, "drive_chegou_at", None)),
        "drive_entregue_at": _to_iso(getattr(pedido, "drive_entregue_at", None)),
        "palavra_chave_retirada": getattr(pedido, "palavra_chave_retirada", None),
        "payment_provider": payment_info.get("payment_provider"),
        "payment_preference_id": payment_info.get("payment_preference_id"),
        "payment_url": payment_info.get("payment_url"),
        "canal": canal,
        "canal_label": channel_label_for(canal),
        "total": _to_float(getattr(pedido, "total", 0)),
        "created_at": _to_iso(getattr(pedido, "created_at", None)),
        "itens_count": len(itens),
        "itens": [_checkout_item_dict(item) for item in itens],
    }


def build_sale_history_entry(venda: Any, *, linked_order: Any | None = None) -> dict:
    canal = normalize_sales_channel(
        getattr(venda, "canal", None), default="loja_fisica"
    )
    pedido_id = getattr(linked_order, "pedido_id", None)
    created_at = getattr(venda, "data_venda", None) or getattr(
        venda, "created_at", None
    )
    itens = list(getattr(venda, "itens", []) or [])
    return {
        "historico_id": f"venda:{getattr(venda, 'id', None)}",
        "origem_tipo": "venda",
        "pedido_id": pedido_id,
        "venda_id": getattr(venda, "id", None),
        "numero": getattr(venda, "numero_venda", None) or str(getattr(venda, "id", "")),
        "status": getattr(venda, "status", None),
        "status_entrega": getattr(venda, "status_entrega", None),
        "retirado_por": getattr(venda, "retirado_por", None),
        "tem_entrega": bool(getattr(venda, "tem_entrega", False)),
        "tipo_retirada": getattr(venda, "tipo_retirada", None)
        or getattr(linked_order, "tipo_retirada", None),
        "is_drive": bool(getattr(linked_order, "is_drive", False)),
        "drive_chegou_at": _to_iso(getattr(linked_order, "drive_chegou_at", None)),
        "drive_entregue_at": _to_iso(getattr(linked_order, "drive_entregue_at", None)),
        "palavra_chave_retirada": getattr(venda, "palavra_chave_retirada", None)
        or getattr(linked_order, "palavra_chave_retirada", None),
        "payment_provider": getattr(linked_order, "payment_provider", None),
        "payment_preference_id": getattr(linked_order, "payment_preference_id", None),
        "payment_url": getattr(linked_order, "payment_url", None),
        "canal": canal,
        "canal_label": channel_label_for(canal),
        "total": _to_float(getattr(venda, "total", 0)),
        "created_at": _to_iso(created_at),
        "itens_count": len(itens),
        "itens": [_sale_item_dict(item) for item in itens],
    }


def merge_history_entries(
    checkout_entries: list[dict],
    sale_entries: list[dict],
    *,
    limit: int,
) -> list[dict]:
    linked_pedido_ids = {
        entry.get("pedido_id") for entry in sale_entries if entry.get("pedido_id")
    }
    visible_checkout = [
        entry
        for entry in checkout_entries
        if not entry.get("pedido_id") or entry.get("pedido_id") not in linked_pedido_ids
    ]
    merged = [*sale_entries, *visible_checkout]
    merged.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return merged[:limit]


def _load_checkout_items(db, pedido_id: str) -> list[PedidoItem]:
    return (
        db.query(PedidoItem)
        .filter(PedidoItem.pedido_id == pedido_id)
        .order_by(PedidoItem.id.asc())
        .all()
    )


def _payment_info_for_pedido(db, pedido: Pedido) -> dict[str, str | None]:
    payment_info = {
        "payment_provider": pedido.payment_provider,
        "payment_preference_id": pedido.payment_preference_id,
        "payment_url": pedido.payment_url,
    }
    if payment_info["payment_url"] or payment_info["payment_preference_id"]:
        return payment_info

    idem_rows = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.user_id == pedido.cliente_id,
            IdempotencyKey.tenant_id == pedido.tenant_id,
            IdempotencyKey.endpoint == CHECKOUT_FINALIZAR_ENDPOINT,
            IdempotencyKey.status == "completed",
            IdempotencyKey.response_body.isnot(None),
            IdempotencyKey.response_body.contains(pedido.pedido_id),
        )
        .order_by(IdempotencyKey.completed_at.desc(), IdempotencyKey.id.desc())
        .limit(5)
        .all()
    )

    for idem_row in idem_rows:
        try:
            response = json.loads(idem_row.response_body or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if response.get("pedido_id") != pedido.pedido_id:
            continue
        return {
            "payment_provider": response.get("payment_provider"),
            "payment_preference_id": response.get("payment_preference_id"),
            "payment_url": response.get("payment_url"),
        }

    return payment_info


def _linked_sale_id_from_registry(db, pedido: Pedido) -> int | None:
    registry = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.user_id == 0,
            IdempotencyKey.tenant_id == pedido.tenant_id,
            IdempotencyKey.endpoint == ECOMMERCE_SALE_INTEGRATION_ENDPOINT,
            IdempotencyKey.chave_idempotencia == f"ecommerce-venda:{pedido.pedido_id}",
            IdempotencyKey.status == "completed",
            IdempotencyKey.response_body.isnot(None),
        )
        .order_by(IdempotencyKey.completed_at.desc(), IdempotencyKey.id.desc())
        .first()
    )
    if not registry or not registry.response_body:
        return None
    try:
        response = json.loads(registry.response_body or "{}")
        return int(response["venda_id"]) if response.get("venda_id") else None
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return None


def _find_linked_sale_for_order(
    db,
    *,
    pedido: Pedido,
    cliente_ids: list[int],
) -> Venda | None:
    sale_id = _linked_sale_id_from_registry(db, pedido)
    if sale_id:
        venda = (
            db.query(Venda)
            .options(joinedload(Venda.itens).joinedload(VendaItem.produto))
            .filter(
                Venda.id == sale_id,
                Venda.tenant_id == pedido.tenant_id,
                Venda.cliente_id.in_(cliente_ids),
            )
            .first()
        )
        if venda:
            return venda

    if not cliente_ids:
        return None

    return (
        db.query(Venda)
        .options(joinedload(Venda.itens).joinedload(VendaItem.produto))
        .filter(
            Venda.tenant_id == pedido.tenant_id,
            Venda.cliente_id.in_(cliente_ids),
            Venda.observacoes.contains(pedido.pedido_id),
        )
        .order_by(Venda.id.desc())
        .first()
    )


def list_customer_order_history(
    db,
    *,
    tenant_id: str,
    user_id: int,
    limit: int = 20,
) -> list[dict]:
    clientes = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.user_id == user_id,
        )
        .all()
    )
    cliente_ids = [cliente.id for cliente in clientes]

    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.cliente_id == user_id,
            Pedido.tenant_id == tenant_id,
            Pedido.status != "carrinho",
        )
        .order_by(Pedido.id.desc())
        .limit(limit)
        .all()
    )

    linked_order_by_sale_id: dict[int, Pedido] = {}
    linked_sale_by_order_id: dict[str, Venda] = {}
    for pedido in pedidos:
        venda = _find_linked_sale_for_order(
            db,
            pedido=pedido,
            cliente_ids=cliente_ids,
        )
        if venda:
            linked_order_by_sale_id[int(venda.id)] = pedido
            linked_sale_by_order_id[pedido.pedido_id] = venda

    vendas: list[Venda] = []
    if cliente_ids:
        vendas = (
            db.query(Venda)
            .options(joinedload(Venda.itens).joinedload(VendaItem.produto))
            .filter(
                Venda.tenant_id == tenant_id,
                Venda.cliente_id.in_(cliente_ids),
            )
            .order_by(Venda.data_venda.desc(), Venda.id.desc())
            .limit(limit)
            .all()
        )

    vendas_by_id = {int(venda.id): venda for venda in vendas}
    for venda in linked_sale_by_order_id.values():
        vendas_by_id[int(venda.id)] = venda

    sale_entries = [
        build_sale_history_entry(
            venda,
            linked_order=linked_order_by_sale_id.get(int(venda.id)),
        )
        for venda in vendas_by_id.values()
    ]

    checkout_entries = [
        build_checkout_history_entry(
            pedido,
            _load_checkout_items(db, pedido.pedido_id),
            payment_info=_payment_info_for_pedido(db, pedido),
            venda_info={},
        )
        for pedido in pedidos
    ]

    return merge_history_entries(checkout_entries, sale_entries, limit=limit)
