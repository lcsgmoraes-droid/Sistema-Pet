"""Leitura local das cobrancas por vinculo exato; nenhuma operacao no provedor.

Cada leitura usa a revisao ativa, inclusive quando o snapshot de rentabilidade
da venda ja foi congelado. Dados de homologacao nunca sao aplicados em producao;
massa sintetica so e exibida por escolha explicita e nunca completa lucro real.
"""

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import or_, select

from app.config import _is_strict_runtime_environment, settings
from app.ifood_financial_cost_models import IfoodFinancialSaleLink
from app.ifood_financial_models import IfoodFinancialEvent, IfoodFinancialSnapshot
from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_order_models import IfoodOrder, IfoodPdvBridge
from app.tenancy.context import get_current_tenant
from app.vendas_models import Venda

from .financial import (
    CONCLUDED_TRIGGERS,
    FEE_NAMES,
    KNOWN_NAMES,
    MODE,
    SOURCE,
    IfoodFinancialError,
)


FEE_LABELS = {
    "ORDER_COMMISSION": "Comissão iFood",
    "PAYMENT_TRANSACTION_FEE": "Taxa de pagamento iFood",
}
NON_FEE_LABELS = {
    "ORDER_PAYMENT": "Pagamento registrado pelo iFood",
    "IFOOD_SUBSIDY": "Subsídio iFood",
    "STORE_SUBSIDY": "Desconto subsidiado pela loja",
}
DEV_ENVIRONMENTS = {"development", "dev", "test", "testing"}
CENT = Decimal("0.01")


def _money(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or abs(result) > Decimal("999999999999.99"):
            return None
        return result.quantize(CENT)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _pending(code, label, reason):
    return {"code": code, "label": label, "reason": reason}


def _fingerprint(result):
    return sha256(
        json.dumps(result, sort_keys=True, ensure_ascii=True, default=str).encode()
    ).hexdigest()


def _empty(reason=None):
    result = {
        "order_id": None,
        "merchant_id": None,
        "mode": MODE,
        "link_source": None,
        "checkout": None,
        "delivery_provider": None,
        "charges": [],
        "non_fee_events": [],
        "pending_components": [
            _pending(code, label, "Cobrança ainda não recebida no Financial.")
            for code, label in FEE_LABELS.items()
        ],
        "fee_known_total": 0.0,
        "fee_total": None,
        "complete": False,
        "simulated": False,
        "simulation_complete": False,
        "simulation_fee_total": None,
    }
    if reason:
        result["pending_components"].append(reason)
    result["fingerprint"] = _fingerprint(result)
    return result


def _delivery_providers(order):
    if not order:
        return set()
    payload = order.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    operation = payload.get("operationMode") or {}
    delivery = operation.get("delivery") or {} if isinstance(operation, dict) else {}
    legacy = payload.get("delivery") or {}
    return {
        str(value).strip().upper()
        for value in (
            order.get("delivered_by"),
            delivery.get("provider") if isinstance(delivery, dict) else None,
            legacy.get("deliveredBy") if isinstance(legacy, dict) else None,
        )
        if value
    }


def _delivery_provider(order):
    values = _delivery_providers(order)
    return (
        next(iter(values))
        if len(values) == 1 and values <= {"MERCHANT", "IFOOD"}
        else None
    )


def _checkout(bridge):
    raw = (bridge or {}).get("online_financial_evidence") or {}
    data = raw.get("checkout") if isinstance(raw, dict) else None
    if not isinstance(data, dict):
        return None
    return {
        key: float(value) if (value := _money(data.get(key))) is not None else None
        for key in (
            "items_total",
            "delivery_fee",
            "ifood_service_fee",
            "operational_total",
            "customer_total",
        )
    }


def _charge(event, snapshot):
    raw = event.get("evidence") or {}
    raw = raw if isinstance(raw, dict) else {}
    billing = raw.get("billing") or {}
    billing = billing if isinstance(billing, dict) else {}
    code = event["name"]
    signed = _money(event["amount"])
    known = code in FEE_NAMES and signed is not None
    simulated = snapshot["source"] == "synthetic"
    return {
        "code": code,
        "label": FEE_LABELS.get(code) or raw.get("description") or code,
        "description": raw.get("description"),
        "amount": float(-signed) if known else None,
        "signed_amount": float(signed) if signed is not None else None,
        "status": "simulated" if simulated else "known" if known else "unclassified",
        "classification": {
            "ORDER_COMMISSION": "commission",
            "PAYMENT_TRANSACTION_FEE": "payment_fee",
        }.get(code, "unclassified"),
        "source": snapshot["source"],
        "snapshot_id": snapshot["id"],
        "revision": snapshot["revision"],
        "position": event["position"],
        "trigger": event["trigger"],
        "has_transfer_impact": event["has_transfer_impact"],
        "billing": {
            "base_value": billing.get("baseValue"),
            "fee_percentage": billing.get("feePercentage"),
        },
    }


def _compose(
    mapping, bridge, order, sale_status, snapshots, events, *, allow_synthetic
):
    result = _empty()
    result.pop("fingerprint")
    result.update(
        order_id=mapping["order_id"],
        merchant_id=mapping["merchant_id"],
        link_source=mapping["source"],
        checkout=_checkout(bridge),
        delivery_provider=_delivery_provider(order),
        pending_components=[],
    )
    order_events = [
        event for event in events if event["order_id"] == mapping["order_id"]
    ]
    involved_ids = {event["snapshot_id"] for event in order_events}
    involved = [snapshots[snapshot_id] for snapshot_id in sorted(involved_ids)]
    simulated = any(snapshot["source"] == "synthetic" for snapshot in involved)
    allowed = [
        event
        for event in order_events
        if snapshots[event["snapshot_id"]]["source"] == SOURCE
        or (
            allow_synthetic and snapshots[event["snapshot_id"]]["source"] == "synthetic"
        )
    ]
    names = {event["name"] for event in allowed if _money(event["amount"]) is not None}
    pending = [
        _pending(code, label, "Cobrança ainda não recebida no Financial.")
        for code, label in FEE_LABELS.items()
        if code not in names
    ]
    for event in allowed:
        snapshot = snapshots[event["snapshot_id"]]
        if event["name"] in NON_FEE_LABELS:
            signed = _money(event["amount"])
            result["non_fee_events"].append(
                {
                    "code": event["name"],
                    "label": NON_FEE_LABELS[event["name"]],
                    "signed_amount": float(signed) if signed is not None else None,
                    "source": snapshot["source"],
                    "snapshot_id": snapshot["id"],
                    "revision": snapshot["revision"],
                    "position": event["position"],
                }
            )
        else:
            result["charges"].append(_charge(event, snapshot))
        if event["name"] not in KNOWN_NAMES:
            pending.append(
                _pending(
                    event["name"],
                    (event.get("evidence") or {}).get("description") or event["name"],
                    "Lançamento recebido, mas a natureza da cobrança ainda precisa ser classificada.",
                )
            )
        if _money(event["amount"]) is None:
            pending.append(
                _pending(
                    "invalid_amount",
                    "Valor financeiro a conferir",
                    "Há um valor monetário inválido na evidência local.",
                )
            )
        if event["trigger"] not in CONCLUDED_TRIGGERS:
            pending.append(
                _pending(
                    "adjustment",
                    "Ajuste ou apuração a conferir",
                    "Há lançamento provisório, ajuste ou cancelamento que exige conciliação.",
                )
            )
    if len(involved_ids) > 1:
        pending.append(
            _pending(
                "multiple_windows",
                "Conciliação entre períodos",
                "O pedido possui lançamentos em mais de uma janela ativa; não somar como fechamento final.",
            )
        )
    if any(
        event["snapshot_id"] in involved_ids and event["order_id"] is None
        for event in events
    ):
        pending.append(
            _pending(
                "unallocated",
                "Lançamentos sem pedido",
                "Há lançamentos não atribuídos a um pedido na mesma janela financeira.",
            )
        )
    if (
        sale_status not in {"finalizada", "baixa_parcial"}
        or (order or {}).get("status") in {"CANCELLED", "CANCELLATION_REQUESTED"}
        or (bridge or {}).get("status") == "cancelled"
    ):
        pending.append(
            _pending(
                "sale_state",
                "Situação da venda a conferir",
                "A venda ou o pedido está aberto, cancelado ou em cancelamento; confira a conciliação.",
            )
        )
    if result["delivery_provider"] == "IFOOD":
        pending.append(
            _pending(
                "delivery_cost",
                "Custo de entrega iFood",
                "A modalidade usa logística iFood; a cobrança precisa ser identificada no extrato, sem confundir frete do cliente com custo da loja.",
            )
        )
    providers = _delivery_providers(order)
    if len(providers) > 1 or providers - {"MERCHANT", "IFOOD"}:
        pending.append(
            _pending(
                "delivery_mode",
                "Modalidade de entrega a conferir",
                "Há informações conflitantes ou uma modalidade ainda não classificada; confira o custo logístico.",
            )
        )
    unsupported = [
        snapshot
        for snapshot in involved
        if snapshot["source"] not in {SOURCE, "synthetic"}
    ]
    if unsupported:
        pending.append(
            _pending(
                "unsupported_source",
                "Origem financeira não confirmada",
                "Os lançamentos não possuem origem Financial suportada.",
            )
        )
    # A lista de eventos e a revisao entram no hash mesmo quando a fonte foi
    # rejeitada: a chegada de dados nunca fica oculta por cache negativo.
    result["evidence_revisions"] = [
        {
            "id": snapshot["id"],
            "revision": snapshot["revision"],
            "source": snapshot["source"],
            "payload_hash": snapshot["payload_hash"],
        }
        for snapshot in involved
    ]
    result["simulated"] = simulated
    result["simulation_complete"] = bool(allow_synthetic and simulated and not pending)
    if simulated:
        pending.append(
            _pending(
                "synthetic_evidence",
                "Simulação Financial em DEV",
                "Massa sintética não comprova cobrança real nem libera lucro final.",
            )
        )
    # Repeticoes identicas de linhas no mesmo extrato sao legitimas e mantidas;
    # apenas mensagens de pendencia equivalentes sao deduplicadas.
    result["pending_components"] = list(
        {json.dumps(item, sort_keys=True): item for item in pending}.values()
    )
    total = sum(
        (
            Decimal(str(charge["amount"]))
            for charge in result["charges"]
            if charge["amount"] is not None
        ),
        Decimal("0"),
    )
    result["fee_known_total"] = float(total.quantize(CENT))
    result["complete"] = not result["pending_components"]
    result["fee_total"] = result["fee_known_total"] if result["complete"] else None
    result["simulation_fee_total"] = (
        result["fee_known_total"] if result["simulation_complete"] else None
    )
    result["fingerprint"] = _fingerprint(result)
    return result


def resolve_sales_financials(
    db, tenant_id, sale_ids, *, mode=MODE, allow_synthetic=False
):
    """Resolve em lote por tenant/loja/pedido/ambiente; leitura sem flush ou rede."""
    tenant = UUID(str(tenant_id))
    current = get_current_tenant()
    if current is not None and str(current) != str(tenant):
        raise IfoodFinancialError(
            "Empresa diferente da sessão selecionada.", status_code=403
        )
    if isinstance(sale_ids, (str, bytes)):
        raise IfoodFinancialError("Informe uma coleção de IDs de vendas.")
    ids = list(
        dict.fromkeys(
            int(value)
            for value in sale_ids
            if not isinstance(value, bool) and str(value).isdigit() and int(value) > 0
        )
    )
    if len(ids) > 10000:
        raise IfoodFinancialError("Consulte no máximo 10000 vendas por relatório.")
    result = {sale_id: _empty() for sale_id in ids}
    if not ids:
        return result
    if (
        _is_strict_runtime_environment()
        or str(settings.ENVIRONMENT).strip().lower() not in DEV_ENVIRONMENTS
        or mode != MODE
    ):
        return {
            sale_id: _empty(
                _pending(
                    "environment",
                    "Financial não habilitado neste ambiente",
                    "Evidências de homologação só são usadas em DEV/teste e nunca completam resultados em produção.",
                )
            )
            for sale_id in ids
        }
    with db.no_autoflush:
        config_table = IfoodMerchantConfig.__table__
        merchant = db.execute(
            select(config_table.c.merchant_id).where(config_table.c.tenant_id == tenant)
        ).scalar_one_or_none()
        if not merchant:
            return {
                sale_id: _empty(
                    _pending(
                        "merchant_binding",
                        "Loja sem vínculo financeiro",
                        "Confira o vínculo da loja iFood desta empresa.",
                    )
                )
                for sale_id in ids
            }
        bridge_table, links_table = (
            IfoodPdvBridge.__table__,
            IfoodFinancialSaleLink.__table__,
        )
        bridges = {
            row["sale_id"]: dict(row)
            for row in db.execute(
                select(bridge_table).where(
                    bridge_table.c.tenant_id == tenant, bridge_table.c.sale_id.in_(ids)
                )
            ).mappings()
        }
        links = {
            row["venda_id"]: dict(row)
            for row in db.execute(
                select(links_table).where(
                    links_table.c.tenant_id == tenant,
                    links_table.c.mode == mode,
                    links_table.c.venda_id.in_(ids),
                )
            ).mappings()
        }
        mappings = {}
        for sale_id in ids:
            candidates = []
            if sale_id in bridges:
                bridge = bridges[sale_id]
                candidates.append(
                    {
                        "order_id": bridge["ifood_order_id"],
                        "merchant_id": bridge["merchant_id"],
                        "source": "pdv_bridge",
                    }
                )
            if sale_id in links:
                link = links[sale_id]
                candidates.append(
                    {
                        "order_id": link["order_id"],
                        "merchant_id": link["merchant_id"],
                        "source": "explicit_confirmation",
                    }
                )
            if not candidates:
                result[sale_id] = _empty(
                    _pending(
                        "sale_link",
                        "Venda sem vínculo com pedido",
                        "Confirme o vínculo exato com o pedido iFood; data ou valor iguais não comprovam a relação.",
                    )
                )
            elif (
                len(
                    {
                        (candidate["merchant_id"], candidate["order_id"])
                        for candidate in candidates
                    }
                )
                != 1
            ):
                result[sale_id] = _empty(
                    _pending(
                        "link_conflict",
                        "Vínculos incompatíveis",
                        "A ponte do PDV e o vínculo financeiro apontam para pedidos diferentes.",
                    )
                )
            elif candidates[0]["merchant_id"] != merchant:
                result[sale_id] = _empty(
                    _pending(
                        "merchant_binding",
                        "Vínculo de loja a conferir",
                        "O pedido pertence a um vínculo anterior; os valores não serão transferidos para outra loja.",
                    )
                )
            else:
                mappings[sale_id] = candidates[0]
        if not mappings:
            return result
        order_ids = {mapping["order_id"] for mapping in mappings.values()}
        orders_table = IfoodOrder.__table__
        orders = {
            row["ifood_order_id"]: dict(row)
            for row in db.execute(
                select(orders_table).where(
                    orders_table.c.tenant_id == tenant,
                    orders_table.c.merchant_id == merchant,
                    orders_table.c.ifood_order_id.in_(order_ids),
                )
            ).mappings()
        }
        snapshots_table = IfoodFinancialSnapshot.__table__
        snapshots = {
            row["id"]: dict(row)
            for row in db.execute(
                select(snapshots_table).where(
                    snapshots_table.c.tenant_id == tenant,
                    snapshots_table.c.merchant_id == merchant,
                    snapshots_table.c.mode == mode,
                    snapshots_table.c.active.is_(True),
                )
            ).mappings()
        }
        events_table = IfoodFinancialEvent.__table__
        events = (
            [
                dict(row)
                for row in db.execute(
                    select(events_table)
                    .where(
                        events_table.c.tenant_id == tenant,
                        events_table.c.snapshot_id.in_(snapshots),
                        or_(
                            events_table.c.order_id.in_(order_ids),
                            events_table.c.order_id.is_(None),
                        ),
                    )
                    .order_by(events_table.c.snapshot_id, events_table.c.position)
                ).mappings()
            ]
            if snapshots
            else []
        )
        venda_table = Venda.__table__
        statuses = dict(
            db.execute(
                select(venda_table.c.id, venda_table.c.status).where(
                    venda_table.c.tenant_id == tenant, venda_table.c.id.in_(mappings)
                )
            ).all()
        )
        by_order = defaultdict(list)
        unallocated = []
        for event in events:
            (
                unallocated
                if event["order_id"] is None
                else by_order[event["order_id"]]
            ).append(event)
        for sale_id, mapping in mappings.items():
            if sale_id not in statuses:
                result[sale_id] = _empty(
                    _pending(
                        "sale_scope",
                        "Venda não encontrada",
                        "A venda não pertence à empresa selecionada.",
                    )
                )
                continue
            result[sale_id] = _compose(
                mapping,
                bridges.get(sale_id),
                orders.get(mapping["order_id"]),
                statuses[sale_id],
                snapshots,
                by_order[mapping["order_id"]] + unallocated,
                allow_synthetic=allow_synthetic,
            )
    return result


def resolve_sale_financials(db, tenant_id, sale_id, **kwargs):
    return resolve_sales_financials(db, tenant_id, [sale_id], **kwargs)[int(sale_id)]
