"""CMV original ERP por vinculo exato, sem custo atual, rede ou escrita operacional.

Nao existe hoje identificador externo canonico na Venda. O vinculo inicial e
uma confirmacao explicita; as leituras seguintes calculam automaticamente a
partir dos comprovantes write-once, conferindo o manifesto da confirmacao.
"""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json

from sqlalchemy import or_, select

from app.ifood_financial_cost_models import IfoodFinancialSaleLink
from app.ifood_financial_models import IfoodFinancialEvent, IfoodFinancialSnapshot
from app.ifood_order_models import IfoodOrder

SOURCE = "erp_original_stock_out"
MODE = "homologation"
MAX_MONEY = Decimal("999999999999.99")


def _error(message, status=422):
    # Import tardio: financial compoe este modulo sem dependencia circular.
    from .financial import IfoodFinancialError

    return IfoodFinancialError(message, status_code=status)


def _scope(db, tenant, merchant, mode, *, lock=False):
    from .financial import _scope as financial_scope

    return financial_scope(db, tenant, merchant, mode, lock=lock)


def _order_id(value):
    from .financial import REFERENCE_ID

    if not isinstance(value, str) or not REFERENCE_ID.fullmatch(value):
        raise _error("Identificação técnica do pedido inválida.")
    return value


def _positive_id(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(str(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _decimal(value, places):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0 or number > MAX_MONEY:
            return None
        if number != number.quantize(Decimal(places)):
            return None
        return number
    except (InvalidOperation, ValueError, TypeError):
        return None


def _iso(value):
    return value.isoformat() if value is not None else None


def _hash(proof):
    return sha256(
        json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _item_cost(item, sale, tenant):
    missing = []
    quantity = _decimal(item["quantidade"], "0.001")
    if item["tipo"] != "produto" or not _positive_id(item["produto_id"]):
        missing.append("Item sem comprovante de custo de produto compatível.")
    if quantity is None:
        missing.append("Quantidade do item inválida ou desconhecida.")
    proof = item["custo_original_saida"]
    cost, movement, captured = None, None, None
    if not isinstance(proof, dict):
        missing.append("Comprovante original da baixa de estoque ausente.")
    else:
        stock_tenant = str(item["estoque_origem_tenant_id"] or tenant)
        identifiers = (
            _positive_id(proof.get("venda_id")) == sale["id"]
            and _positive_id(proof.get("venda_item_id")) == item["id"]
            and _positive_id(proof.get("produto_id")) == item["produto_id"]
            and _positive_id(proof.get("movimentacao_id")) is not None
            and proof.get("versao") == 1
            and not isinstance(proof.get("versao"), bool)
            and proof.get("origem") == "baixa_estoque_venda"
            and proof.get("tenant_estoque_id") == stock_tenant
        )
        proof_quantity = _decimal(proof.get("quantidade"), "0.001")
        cost = _decimal(proof.get("custo_total"), "0.01")
        try:
            captured = datetime.fromisoformat(proof.get("capturado_em", ""))
            if captured.tzinfo is None:
                raise ValueError
        except (ValueError, TypeError):
            captured = None
        if (
            not identifiers
            or quantity is None
            or proof_quantity != quantity
            or cost is None
            or captured is None
        ):
            missing.append(
                "Comprovante original incompatível com os IDs, quantidade, origem ou valor do item."
            )
        else:
            movement = _positive_id(proof["movimentacao_id"])
    return {
        "sale_item_id": item["id"],
        "product_id": item["produto_id"],
        "quantity": str(quantity) if quantity is not None else None,
        "cost": f"{cost:.2f}" if cost is not None and not missing else None,
        "movement_id": movement,
        "proof_captured_at": _iso(captured),
        "status": "pending" if missing else "verified",
        "missing": missing,
    }


def _manifest(items):
    return [
        {
            "id": item["id"],
            "product_id": item["produto_id"],
            "type": item["tipo"],
            "quantity": str(item["quantidade"]),
            "stock_tenant_id": str(item["estoque_origem_tenant_id"] or ""),
            "proof_hash": _hash(item["custo_original_saida"]),
        }
        for item in items
    ]


def _empty():
    return {
        "status": "pending",
        "cmv": None,
        "source": SOURCE,
        "sale": None,
        "items": [],
        "link": None,
        "missing": ["Pedido sem vínculo explícito com a venda do ERP."],
    }


def _sale_view(sale, items, tenant, *, returned=False, link=None):
    result = _empty()
    missing = []
    result["sale"] = {
        "id": sale["id"],
        "number": sale["numero_venda"],
        "date": _iso(sale["data_venda"]),
        "status": sale["status"],
    }
    if sale["canal"] != "ifood":
        missing.append("A venda ERP não pertence ao canal iFood.")
    if (
        sale["status"] != "finalizada"
        or sale["data_cancelamento"] is not None
        or sale["cancelada_por"] is not None
    ):
        missing.append("A venda ERP não está finalizada ou possui cancelamento.")
    if returned:
        missing.append(
            "Venda com devolução ou estorno; conciliação do custo necessária."
        )
    if not items:
        missing.append("Venda sem conjunto de itens comprovado.")
    result["items"] = [_item_cost(item, sale, tenant) for item in items]
    if any(item["missing"] for item in result["items"]):
        missing.append("Há itens sem custo original integralmente comprovado.")
    movements = [
        item["movement_id"]
        for item in result["items"]
        if item["movement_id"] is not None
    ]
    if len(movements) != len(set(movements)):
        missing.append("Movimentação de estoque repetida em mais de um item da venda.")
    if link is not None:
        result["link"] = {
            "id": link["id"],
            "source": link["source"],
            "actor_id": link["actor_id"],
            "linked_at": _iso(link["created_at"]),
            "source_note": link["source_note"],
        }
        if link["item_manifest"] != _manifest(items):
            missing.append(
                "O conjunto de itens ou comprovantes mudou após o vínculo; revisão necessária."
            )
    if not missing:
        total = sum((Decimal(item["cost"]) for item in result["items"]), Decimal("0"))
        if total > MAX_MONEY:
            missing.append("O custo total excede a faixa monetária suportada.")
        else:
            result.update(status="verified", cmv=f"{total:.2f}")
    result["missing"] = missing
    return result


def _sale_data(db, tenant, sale_ids, *, lock=False):
    from app.vendas_devolucoes_models import VendaDevolucao
    from app.vendas_models import Venda, VendaItem

    sales_table, items_table = Venda.__table__, VendaItem.__table__
    sales_query = select(
        sales_table.c.id,
        sales_table.c.numero_venda,
        sales_table.c.data_venda,
        sales_table.c.status,
        sales_table.c.canal,
        sales_table.c.data_cancelamento,
        sales_table.c.cancelada_por,
    ).where(sales_table.c.tenant_id == tenant, sales_table.c.id.in_(sale_ids))
    items_query = (
        select(
            items_table.c.id,
            items_table.c.venda_id,
            items_table.c.produto_id,
            items_table.c.tipo,
            items_table.c.quantidade,
            items_table.c.custo_original_saida,
            items_table.c.estoque_origem_tenant_id,
        )
        .where(items_table.c.tenant_id == tenant, items_table.c.venda_id.in_(sale_ids))
        .order_by(items_table.c.id)
    )
    if lock:
        sales_query = sales_query.with_for_update()
        items_query = items_query.with_for_update()
    sales = {sale["id"]: sale for sale in db.execute(sales_query).mappings()}
    items = defaultdict(list)
    for item in db.execute(items_query).mappings():
        items[item["venda_id"]].append(item)
    returns = VendaDevolucao.__table__
    returned_ids = set(
        db.execute(
            select(returns.c.venda_id).where(
                returns.c.tenant_id == tenant, returns.c.venda_id.in_(sale_ids)
            )
        ).scalars()
    )
    return sales, items, returned_ids


def get_historical_costs_for_orders(db, tenant_id, merchant_id, order_ids, mode=MODE):
    """Numero fixo de consultas por lote; nao consulta Produto nem custo atual."""
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode)
    if isinstance(order_ids, (str, bytes)):
        raise _error("Informe uma coleção de identificadores de pedidos.")
    ids = list(dict.fromkeys(_order_id(order_id) for order_id in order_ids))
    if len(ids) > 10000:
        raise _error("Consulte no máximo 10000 pedidos por relatório.")
    result = {}
    for start in range(0, len(ids), 1000):
        result.update(
            _historical_batch(db, tenant, merchant, ids[start : start + 1000], mode)
        )
    return result


def _historical_batch(db, tenant, merchant, ids, mode):
    result = {order_id: _empty() for order_id in ids}
    table = IfoodFinancialSaleLink.__table__
    links = list(
        db.execute(
            select(table).where(
                table.c.tenant_id == tenant,
                table.c.merchant_id == merchant,
                table.c.mode == mode,
                table.c.order_id.in_(ids),
            )
        ).mappings()
    )
    sale_ids = [link["venda_id"] for link in links]
    if not sale_ids:
        return result
    sales, items, returned = _sale_data(db, tenant, sale_ids)
    for link in links:
        sale = sales.get(link["venda_id"])
        if sale is None:
            result[link["order_id"]]["missing"] = [
                "Venda vinculada não disponível nesta empresa."
            ]
        else:
            result[link["order_id"]] = _sale_view(
                sale,
                items[sale["id"]],
                tenant,
                returned=sale["id"] in returned,
                link=link,
            )
    orders = IfoodOrder.__table__
    for order in db.execute(
        select(orders.c.ifood_order_id, orders.c.status).where(
            orders.c.tenant_id == tenant,
            orders.c.merchant_id == merchant,
            orders.c.ifood_order_id.in_(ids),
        )
    ).mappings():
        if order["status"] in {"CANCELLED", "CANCELLATION_REQUESTED"}:
            cost = result[order["ifood_order_id"]]
            cost.update(status="pending", cmv=None)
            cost["missing"].append(
                "Pedido iFood cancelado ou com cancelamento solicitado; conciliação necessária."
            )
    return result


def get_order_historical_cost(db, tenant_id, merchant_id, order_id, mode=MODE):
    return get_historical_costs_for_orders(
        db, tenant_id, merchant_id, [order_id], mode
    )[order_id]


def _financial_order_exists(db, tenant, merchant, mode, order_id):
    events, snapshots = IfoodFinancialEvent.__table__, IfoodFinancialSnapshot.__table__
    return (
        db.execute(
            select(events.c.id)
            .join(
                snapshots,
                (events.c.snapshot_id == snapshots.c.id)
                & (events.c.tenant_id == snapshots.c.tenant_id),
            )
            .where(
                events.c.tenant_id == tenant,
                snapshots.c.tenant_id == tenant,
                snapshots.c.merchant_id == merchant,
                snapshots.c.mode == mode,
                snapshots.c.active.is_(True),
                events.c.order_id == order_id,
            )
            .limit(1)
        ).first()
        is not None
    )


def link_order_sale(
    db, tenant_id, merchant_id, order_id, venda_id, source_note, actor_id, mode=MODE
):
    """Confirmacao humana exata; nao cria venda nem altera qualquer custo original."""
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode, lock=True)
    order_id = _order_id(order_id)
    sale_id = _positive_id(venda_id)
    if (
        sale_id is None
        or not isinstance(actor_id, int)
        or isinstance(actor_id, bool)
        or actor_id <= 0
    ):
        raise _error("Identificação da venda ou usuário responsável inválida.")
    if (
        not isinstance(source_note, str)
        or not 1 <= len(source_note.strip()) <= 1000
        or not source_note.isprintable()
    ):
        raise _error("Informe a justificativa do vínculo, com até 1000 caracteres.")
    if not _financial_order_exists(db, tenant, merchant, mode, order_id):
        raise _error("Pedido financeiro não encontrado nesta loja e ambiente.", 404)
    table = IfoodFinancialSaleLink.__table__
    existing = list(
        db.execute(
            select(table).where(
                table.c.tenant_id == tenant,
                table.c.mode == mode,
                or_(
                    (table.c.merchant_id == merchant) & (table.c.order_id == order_id),
                    table.c.venda_id == sale_id,
                ),
            )
        ).mappings()
    )
    if existing:
        if (
            len(existing) == 1
            and existing[0]["venda_id"] == sale_id
            and existing[0]["merchant_id"] == merchant
            and existing[0]["order_id"] == order_id
        ):
            return get_order_historical_cost(db, tenant, merchant, order_id, mode)
        raise _error(
            "Pedido ou venda já possui outro vínculo histórico; não será substituído.",
            409,
        )
    sales, items, returned = _sale_data(db, tenant, [sale_id], lock=True)
    sale = sales.get(sale_id)
    if sale is None:
        raise _error("Venda ERP não encontrada nesta empresa.", 404)
    cost = _sale_view(sale, items[sale_id], tenant, returned=sale_id in returned)
    if cost["status"] != "verified":
        raise _error(" ".join(cost["missing"]), 409)
    order_table = IfoodOrder.__table__
    cancelled = db.execute(
        select(order_table.c.id).where(
            order_table.c.tenant_id == tenant,
            order_table.c.merchant_id == merchant,
            order_table.c.ifood_order_id == order_id,
            order_table.c.status.in_(["CANCELLED", "CANCELLATION_REQUESTED"]),
        )
    ).first()
    if cancelled is not None:
        raise _error(
            "Pedido iFood cancelado ou em cancelamento; conciliação necessária.", 409
        )
    db.execute(
        table.insert().values(
            tenant_id=tenant,
            merchant_id=merchant,
            mode=mode,
            order_id=order_id,
            venda_id=sale_id,
            source="explicit_confirmation",
            source_note=source_note.strip(),
            actor_id=actor_id,
            item_manifest=_manifest(items[sale_id]),
        )
    )
    db.flush()
    return get_order_historical_cost(db, tenant, merchant, order_id, mode)


def list_linkable_sales(db, tenant_id, merchant_id, search="", limit=20, mode=MODE):
    """Lista por numero/ID informado. Nunca escolhe venda por coincidencia financeira."""
    from app.vendas_models import Venda

    tenant, merchant = _scope(db, tenant_id, merchant_id, mode)
    if (
        not isinstance(search, str)
        or len(search) > 80
        or (search and not search.isprintable())
    ):
        raise _error("Busca de venda inválida.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise _error("O limite deve ser de 1 a 50 vendas.")
    table = Venda.__table__
    query = select(table.c.id).where(
        table.c.tenant_id == tenant, table.c.canal == "ifood"
    )
    search = search.strip()
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        expression = table.c.numero_venda.ilike(f"%{escaped}%", escape="\\")
        sale_id = _positive_id(search)
        if sale_id is not None:
            expression = table.c.id == sale_id
        query = query.where(expression)
    ids = list(db.execute(query.order_by(table.c.id.desc()).limit(limit)).scalars())
    sales, items, returned = _sale_data(db, tenant, ids)
    links = IfoodFinancialSaleLink.__table__
    linked_ids = set(
        db.execute(
            select(links.c.venda_id).where(
                links.c.tenant_id == tenant,
                links.c.mode == mode,
                links.c.venda_id.in_(ids),
            )
        ).scalars()
    )
    result = []
    for sale_id in ids:
        cost = _sale_view(
            sales[sale_id], items[sale_id], tenant, returned=sale_id in returned
        )
        missing = list(cost["missing"])
        if sale_id in linked_ids:
            missing.append("Venda já vinculada a um pedido financeiro.")
        result.append(
            {
                "venda_id": sale_id,
                "numero": cost["sale"]["number"],
                "data": cost["sale"]["date"],
                "status": cost["sale"]["status"],
                "linkable": not missing,
                "missing": missing,
            }
        )
    return {"sales": result, "limit": limit}
