"""Snapshots completos de Financial Events; nenhuma operacao de rede ou caixa."""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.ifood_financial_models import (
    IfoodFinancialEvent,
    IfoodFinancialOrderCosts,
    IfoodFinancialSnapshot,
)
from app.ifood_integration_models import IfoodMerchantConfig
from app.tenancy.context import get_current_tenant

CENT = Decimal("0.01")
MAX_MONEY = Decimal("999999999999.99")
MODE = "homologation"
SOURCE = "ifood_financial_events"
SOURCES = {SOURCE, "synthetic"}
FEE_NAMES = {"ORDER_COMMISSION", "PAYMENT_TRANSACTION_FEE"}
KNOWN_NAMES = FEE_NAMES | {"ORDER_PAYMENT", "IFOOD_SUBSIDY", "STORE_SUBSIDY"}
CONCLUDED_TRIGGERS = {"SALE_CONCLUDED", "ORDER_CONCLUDED"}
MONEY_FIELDS = ("revenue", "cmv", "tax", "other_costs")
TOTAL_FIELDS = (
    "registered_payments",
    "ifood_subsidy",
    "store_subsidy",
    "fees",
    "transfer_impact",
)
LABEL = "Contribuição com custos informados"
TECHNICAL_CODE = re.compile(r"^[A-Z0-9_./ -]{1,100}$")
REFERENCE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


class IfoodFinancialError(ValueError):
    def __init__(self, message: str, *, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _money(value: Any, *, nullable=False, nonnegative=False) -> Decimal | None:
    if value is None and nullable:
        return None
    if value is None or isinstance(value, bool):
        raise IfoodFinancialError(
            "Informe um valor monetário válido; desconhecido deve ser nulo."
        )
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or abs(amount) > MAX_MONEY:
            raise ValueError
        if nonnegative and amount < 0:
            raise ValueError
        rounded = amount.quantize(CENT)
        if amount != rounded:
            raise ValueError
        return rounded
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise IfoodFinancialError(
            "Valor monetário inválido ou fora da faixa de centavos."
        ) from exc


def _date(value: Any) -> date:
    try:
        if isinstance(value, datetime):
            raise ValueError
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise IfoodFinancialError(
            "Informe datas válidas no formato AAAA-MM-DD."
        ) from exc


def _period(begin_date, end_date):
    begin, end = _date(begin_date), _date(end_date)
    if end < begin or (end - begin).days > 32:
        raise IfoodFinancialError(
            "A janela deve ter de 1 a 33 dias, incluindo início e fim."
        )
    return begin, end


def _scope(db, tenant_id, merchant_id, mode, *, lock=False):
    try:
        tenant, merchant = UUID(str(tenant_id)), str(UUID(str(merchant_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise IfoodFinancialError("Identificação da empresa ou loja inválida.") from exc
    current = get_current_tenant()
    if current is not None and str(current) != str(tenant):
        raise IfoodFinancialError(
            "Empresa diferente da sessão selecionada.", status_code=403
        )
    if mode != MODE:
        raise IfoodFinancialError(
            "Esta etapa financeira está disponível somente em homologation."
        )
    query = db.query(IfoodMerchantConfig).filter(
        IfoodMerchantConfig.tenant_id == tenant,
        IfoodMerchantConfig.merchant_id == merchant,
    )
    if lock:
        query = query.with_for_update()
    if query.first() is None:
        raise IfoodFinancialError(
            "A loja não corresponde ao vínculo atual desta empresa.", status_code=409
        )
    return tenant, merchant


def _actor(actor_id):
    if isinstance(actor_id, bool) or not isinstance(actor_id, int) or actor_id <= 0:
        raise IfoodFinancialError("Usuário responsável inválido.")
    return actor_id


def _code(value, *, required=True):
    if isinstance(value, str) and TECHNICAL_CODE.fullmatch(value):
        return value
    if not required:
        return None
    raise IfoodFinancialError("Evento com identificação técnica inválida.")


def _event_label(value, *, required=True):
    # Official homologation includes human names such as package charges in
    # Portuguese. Keep them as unclassified evidence rather than discarding the
    # entire window. Enum fields (trigger, product, payment) remain strict.
    if (
        isinstance(value, str)
        and 1 <= len(value.strip()) <= 100
        and value.isprintable()
        and re.fullmatch(r"[\w ./()-]+", value)
    ):
        return value.strip()
    if not required and value is None:
        return None
    raise IfoodFinancialError("Nome ou descrição do lançamento financeiro inválido.")


def _timestamp(value):
    if value is None:
        return None
    try:
        if not isinstance(value, str):
            raise ValueError
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError
        return result.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError, OverflowError) as exc:
        raise IfoodFinancialError("Data de referência financeira inválida.") from exc


def _sanitize_event(raw, merchant, begin, end):
    if not isinstance(raw, dict):
        raise IfoodFinancialError("O provedor retornou um evento financeiro inválido.")
    receiver = raw.get("receiver")
    if not isinstance(receiver, dict):
        raise IfoodFinancialError("Evento sem identificação da loja recebedora.")
    if "businessId" in receiver or "businessType" in receiver:
        # Guard local conservador: a Reference nao define equivalencia universal
        # de businessId com merchantId, apenas mostra MERCHANT como exemplo.
        receiver_matches = (
            receiver.get("businessType") == "MERCHANT"
            and receiver.get("businessId") == merchant
        )
        if "merchantId" in receiver:
            receiver_matches = receiver_matches and receiver["merchantId"] == merchant
        sanitized_receiver = {"businessType": "MERCHANT", "businessId": merchant}
    else:
        # Compatibilidade com o contrato anterior do guia Financial Events.
        receiver_matches = receiver.get("merchantId") == merchant
        sanitized_receiver = {"merchantId": merchant}
    if not receiver_matches:
        raise IfoodFinancialError("Evento financeiro pertence a outra loja.")
    period = raw.get("period")
    if not isinstance(period, dict):
        raise IfoodFinancialError("Evento sem período financeiro confirmado.")
    event_begin, event_end = _period(period.get("beginDate"), period.get("endDate"))
    if event_begin < begin or event_end > end:
        raise IfoodFinancialError("Evento fora da janela financeira consultada.")
    reference = raw.get("reference")
    if reference is None:
        reference = {}
    if not isinstance(reference, dict):
        raise IfoodFinancialError("Evento com referência financeira inválida.")
    reference_type = _code(reference.get("type"), required=False)
    reference_id = reference.get("id")
    if reference_id is not None and (
        not isinstance(reference_id, str) or not REFERENCE_ID.fullmatch(reference_id)
    ):
        raise IfoodFinancialError("Referência do evento financeiro inválida.")
    transfer = raw.get("hasTransferImpact")
    if not isinstance(transfer, bool):
        raise IfoodFinancialError("Evento sem informação válida de impacto no repasse.")
    amount = raw.get("amount")
    if not isinstance(amount, dict):
        raise IfoodFinancialError("Evento sem valor financeiro confirmado.")
    amount = _money(amount.get("value"))
    result = {
        "name": _event_label(raw.get("name")),
        "description": _code(raw.get("description"), required=False),
        "product": _code(raw.get("product"), required=False),
        "trigger": _code(raw.get("trigger")),
        "period": {"beginDate": str(event_begin), "endDate": str(event_end)},
        "reference": {
            "type": reference_type,
            "id": reference_id,
            "date": _timestamp(reference.get("date")),
        },
        "hasTransferImpact": transfer,
        "amount": {"value": _text(amount)},
        "receiver": sanitized_receiver,
    }
    if raw.get("dateTime") is not None:
        result["dateTime"] = _timestamp(raw["dateTime"])
    competence = raw.get("competence")
    if competence is not None:
        if not isinstance(competence, str) or not re.fullmatch(
            r"\d{4}-(0[1-9]|1[0-2])", competence
        ):
            raise IfoodFinancialError("Competência financeira inválida.")
        result["competence"] = competence
    billing = raw.get("billing")
    if billing is not None:
        if not isinstance(billing, dict):
            raise IfoodFinancialError("Informações de cobrança inválidas.")
        result["billing"] = {}
        if billing.get("baseValue") is not None:
            result["billing"]["baseValue"] = _text(_money(billing["baseValue"]))
        if billing.get("feePercentage") is not None:
            try:
                fee = Decimal(str(billing["feePercentage"]))
                if (
                    not fee.is_finite()
                    or abs(fee) > 1000
                    or fee.as_tuple().exponent < -6
                ):
                    raise ValueError
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise IfoodFinancialError("Percentual de cobrança inválido.") from exc
            result["billing"]["feePercentage"] = str(fee)
    settlement = raw.get("settlement")
    if settlement is not None:
        if not isinstance(settlement, dict):
            raise IfoodFinancialError("Informação de repasse inválida.")
        if settlement.get("expectedDate") is not None:
            result["settlement"] = {
                "expectedDate": str(_date(settlement["expectedDate"]))
            }
    payment = raw.get("payment")
    if payment is not None:
        if not isinstance(payment, dict):
            raise IfoodFinancialError("Informação de pagamento inválida.")
        result["payment"] = {
            "method": _code(payment.get("method"), required=False),
            "liability": _code(payment.get("liability"), required=False),
        }
    return result


def _parse_pages(pages, merchant, begin, end):
    if not isinstance(pages, list) or not pages or len(pages) > 1000:
        raise IfoodFinancialError(
            "A consulta deve conter todas as páginas financeiras completas."
        )
    sanitized, size = [], None
    for index, page in enumerate(pages, 1):
        if not isinstance(page, dict):
            raise IfoodFinancialError("Página financeira inválida.")
        page_number, page_size = page.get("page"), page.get("size")
        if (
            isinstance(page_number, bool)
            or not isinstance(page_number, int)
            or page_number != index
        ):
            raise IfoodFinancialError(
                "A paginação financeira está incompleta ou fora de ordem."
            )
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 100
        ):
            raise IfoodFinancialError("Tamanho da página financeira inválido.")
        if size is None:
            size = page_size
        if size != page_size:
            raise IfoodFinancialError("O tamanho das páginas mudou durante a consulta.")
        has_next = page.get("hasNextPage")
        if not isinstance(has_next, bool) or has_next != (index < len(pages)):
            raise IfoodFinancialError("A consulta financeira terminou parcialmente.")
        events = page.get("financialEvents")
        if not isinstance(events, list) or len(events) > page_size:
            raise IfoodFinancialError("Página sem a lista financeira completa.")
        sanitized.extend(
            _sanitize_event(event, merchant, begin, end) for event in events
        )
    return sanitized


def _text(value):
    return None if value is None else format(Decimal(value).quantize(CENT), ".2f")


def _iso(value):
    if value is None:
        return None
    return (
        value.replace(tzinfo=value.tzinfo or timezone.utc)
        .astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _snapshot_query(db, tenant, merchant, mode):
    return db.query(IfoodFinancialSnapshot).filter(
        IfoodFinancialSnapshot.tenant_id == tenant,
        IfoodFinancialSnapshot.merchant_id == merchant,
        IfoodFinancialSnapshot.mode == mode,
    )


def _costs_view(cost):
    if cost is None:
        return None
    return {
        "version": cost.version,
        **{field: _text(getattr(cost, field)) for field in MONEY_FIELDS},
        "source_note": cost.source_note,
        "actor_id": cost.actor_id,
        "recorded_at": _iso(cost.created_at),
    }


def _costs_query(db, tenant, merchant, mode):
    return db.query(IfoodFinancialOrderCosts).filter(
        IfoodFinancialOrderCosts.tenant_id == tenant,
        IfoodFinancialOrderCosts.merchant_id == merchant,
        IfoodFinancialOrderCosts.mode == mode,
    )


def _event_view(event):
    raw = event.evidence
    return {
        "position": event.position,
        "name": event.name,
        "description": raw.get("description"),
        "trigger": event.trigger,
        "date_time": raw.get("dateTime"),
        "amount": _text(event.amount),
        "has_transfer_impact": event.has_transfer_impact,
        "payment_method": raw.get("payment", {}).get("method"),
        "payment_liability": raw.get("payment", {}).get("liability"),
        "expected_settlement_date": raw.get("settlement", {}).get("expectedDate"),
        "billing": {
            "base_value": raw.get("billing", {}).get("baseValue"),
            "fee_percentage": raw.get("billing", {}).get("feePercentage"),
        },
    }


def _totals(events):
    result = dict.fromkeys(TOTAL_FIELDS, Decimal("0"))
    for event in events:
        amount = event.amount
        key = {
            "ORDER_PAYMENT": "registered_payments",
            "IFOOD_SUBSIDY": "ifood_subsidy",
            "STORE_SUBSIDY": "store_subsidy",
        }.get(event.name)
        if key:
            result[key] += amount
        if event.name in FEE_NAMES:
            result["fees"] += amount
        if event.has_transfer_impact:
            result["transfer_impact"] += amount
    return {key: _text(value) for key, value in result.items()}


def _order_view(order_id, events, costs, *, unallocated=False, multiple_windows=False):
    totals, pending = _totals(events), []
    names = {event.name for event in events}
    if "ORDER_COMMISSION" not in names:
        pending.append(
            "Comissão ainda não informada pelo iFood; ausência de lançamento não confirma taxa zero."
        )
    if "PAYMENT_TRANSACTION_FEE" not in names:
        pending.append(
            "Taxa de pagamento ainda não informada pelo iFood; ausência de lançamento não confirma taxa zero."
        )
    if any(event.name not in KNOWN_NAMES for event in events):
        pending.append("Há tipos de evento ainda não classificados neste pedido.")
    if any(event.trigger not in CONCLUDED_TRIGGERS for event in events):
        pending.append(
            "Há apuração provisória, ajuste ou cancelamento a conferir neste pedido."
        )
    if unallocated:
        pending.append(
            "Há lançamentos da janela sem pedido; o impacto ainda precisa ser conferido."
        )
    if multiple_windows:
        pending.append(
            "Pedido possui lançamentos em outros períodos; conciliação necessária."
        )
    values = {field: getattr(costs, field) if costs else None for field in MONEY_FIELDS}
    labels = {
        "revenue": "Receita da loja antes das taxas",
        "cmv": "CMV da venda",
        "tax": "Tributos da venda",
        "other_costs": "Outros custos da venda",
    }
    missing = [label for field, label in labels.items() if values[field] is None]
    missing.extend(pending)
    contribution = {
        "calculated": False,
        "amount": None,
        "percent": None,
        "label": LABEL,
        "missing": missing,
    }
    if not missing:
        # Pagamentos/subsidios nao sao adicionados: a receita foi confirmada pelo operador.
        # STORE_SUBSIDY ja esta refletido no pagamento; nao subtrair novamente.
        amount = (
            values["revenue"]
            + Decimal(totals["fees"])
            - values["cmv"]
            - values["tax"]
            - values["other_costs"]
        )
        contribution.update(
            calculated=True,
            amount=_text(amount),
            percent=_text(
                (amount / values["revenue"] * 100).quantize(
                    CENT, rounding=ROUND_HALF_UP
                )
            )
            if values["revenue"] > 0
            else None,
        )
    return {
        "order_id": order_id,
        "events": [_event_view(event) for event in events],
        "totals": totals,
        "manual_costs": _costs_view(costs),
        "contribution": contribution,
        "pending": pending,
    }


def get_financial_report(
    db: Session, tenant_id, merchant_id, begin_date, end_date, mode=MODE
):
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode)
    begin, end = _period(begin_date, end_date)
    snapshot = (
        _snapshot_query(db, tenant, merchant, mode)
        .filter(
            IfoodFinancialSnapshot.begin_date == begin,
            IfoodFinancialSnapshot.end_date == end,
            IfoodFinancialSnapshot.active.is_(True),
        )
        .first()
    )
    report = {
        "mode": mode,
        "merchant_id": merchant,
        "begin_date": str(begin),
        "end_date": str(end),
        "imported": snapshot is not None,
        "metadata": {
            "source": snapshot.source if snapshot else None,
            "completeness": "complete" if snapshot else "not_imported",
            "retrieved_at": _iso(snapshot.created_at) if snapshot else None,
            "snapshot_id": snapshot.id if snapshot else None,
            "revision": snapshot.revision if snapshot else None,
            "page_count": snapshot.page_count if snapshot else 0,
            "event_count": snapshot.event_count if snapshot else 0,
        },
        "summary": {
            "order_count": 0,
            "event_count": 0,
            **dict.fromkeys(TOTAL_FIELDS),
            "unallocated_events": 0,
            "pending_orders": 0,
        },
        "orders": [],
        "unallocated_events": [],
        "warnings": [
            "Extrato de homologação. Recebimentos e impacto no repasse não comprovam crédito bancário nem lucro final.",
            "A conferência das cobranças e a conciliação do repasse continuam pendentes, mesmo quando a contribuição com custos informados está calculada.",
        ],
    }
    if snapshot is None:
        return report
    events = (
        db.query(IfoodFinancialEvent)
        .filter(
            IfoodFinancialEvent.tenant_id == tenant,
            IfoodFinancialEvent.snapshot_id == snapshot.id,
        )
        .order_by(IfoodFinancialEvent.position)
        .all()
    )
    groups = defaultdict(list)
    unallocated = [event for event in events if event.order_id is None]
    for event in events:
        if event.order_id is not None:
            groups[event.order_id].append(event)
    costs = {}
    for cost in (
        _costs_query(db, tenant, merchant, mode)
        .order_by(IfoodFinancialOrderCosts.version.desc())
        .all()
    ):
        costs.setdefault(cost.order_id, cost)
    active_ids = (
        _snapshot_query(db, tenant, merchant, mode)
        .filter(IfoodFinancialSnapshot.active.is_(True))
        .with_entities(IfoodFinancialSnapshot.id)
    )
    order_windows = defaultdict(set)
    if groups:
        for order_id, snapshot_id in (
            db.query(IfoodFinancialEvent.order_id, IfoodFinancialEvent.snapshot_id)
            .filter(
                IfoodFinancialEvent.tenant_id == tenant,
                IfoodFinancialEvent.snapshot_id.in_(active_ids),
                IfoodFinancialEvent.order_id.in_(groups),
            )
            .all()
        ):
            order_windows[order_id].add(snapshot_id)
    report["orders"] = [
        _order_view(
            order_id,
            entries,
            costs.get(order_id),
            unallocated=bool(unallocated),
            multiple_windows=len(order_windows[order_id]) > 1,
        )
        for order_id, entries in groups.items()
    ]
    report["unallocated_events"] = [_event_view(event) for event in unallocated]
    report["summary"] = {
        "order_count": len(groups),
        "event_count": len(events),
        **_totals(events),
        "unallocated_events": len(unallocated),
        "pending_orders": sum(
            not order["contribution"]["calculated"] for order in report["orders"]
        ),
    }
    if snapshot.source == "synthetic":
        report["warnings"].append(
            "Dados sintéticos de DEV; não são cobranças reais do iFood."
        )
    return report


def import_financial_pages(
    db: Session,
    tenant_id,
    merchant_id,
    begin_date,
    end_date,
    pages,
    actor_id,
    mode=MODE,
    source=SOURCE,
):
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode)
    begin, end = _period(begin_date, end_date)
    actor = _actor(actor_id)
    if source not in SOURCES:
        raise IfoodFinancialError("Origem da evidência financeira inválida.")
    evidence = _parse_pages(pages, merchant, begin, end)
    digest = sha256(
        json.dumps(
            evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()
    try:
        # Serializa importacoes da loja, inclusive janelas diferentes, contra sobreposicao.
        _scope(db, tenant, merchant, mode, lock=True)
        snapshots = (
            _snapshot_query(db, tenant, merchant, mode)
            .filter(
                IfoodFinancialSnapshot.active.is_(True),
                IfoodFinancialSnapshot.begin_date <= end,
                IfoodFinancialSnapshot.end_date >= begin,
            )
            .all()
        )
        if any(
            snapshot.begin_date != begin or snapshot.end_date != end
            for snapshot in snapshots
        ):
            raise IfoodFinancialError(
                "Existe outra janela sobreposta. Consulte ou atualize a janela original.",
                status_code=409,
            )
        previous = snapshots[0] if snapshots else None
        revision = previous.revision + 1 if previous else 1
        if previous:
            previous.active = False
            db.flush()
        snapshot = IfoodFinancialSnapshot(
            tenant_id=tenant,
            merchant_id=merchant,
            mode=mode,
            begin_date=begin,
            end_date=end,
            revision=revision,
            active=True,
            source=source,
            payload_hash=digest,
            page_count=len(pages),
            event_count=len(evidence),
            actor_id=actor,
        )
        db.add(snapshot)
        db.flush()
        for position, entry in enumerate(evidence, 1):
            db.add(
                IfoodFinancialEvent(
                    tenant_id=tenant,
                    snapshot_id=snapshot.id,
                    position=position,
                    order_id=entry["reference"]["id"]
                    if entry["reference"]["type"] == "ORDER"
                    else None,
                    name=entry["name"],
                    trigger=entry["trigger"],
                    amount=Decimal(entry["amount"]["value"]),
                    has_transfer_impact=entry["hasTransferImpact"],
                    evidence=entry,
                )
            )
        db.flush()
    except Exception:
        db.rollback()
        raise
    return get_financial_report(db, tenant, merchant, begin, end, mode)


def record_order_costs(
    db: Session, tenant_id, merchant_id, order_id, data, actor_id, mode=MODE
):
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode)
    actor = _actor(actor_id)
    if not isinstance(order_id, str) or not REFERENCE_ID.fullmatch(order_id):
        raise IfoodFinancialError("Pedido financeiro inválido.")
    if not isinstance(data, dict) or set(data) - {*MONEY_FIELDS, "source_note"}:
        raise IfoodFinancialError("Campos de custo informados inválidos.")
    note = data.get("source_note")
    if not isinstance(note, str) or not 5 <= len(note.strip()) <= 1000:
        raise IfoodFinancialError(
            "Informe a fonte e justificativa dos valores (5 a 1000 caracteres)."
        )
    amounts = {
        field: _money(data.get(field), nullable=True, nonnegative=True)
        for field in MONEY_FIELDS
    }
    try:
        _scope(db, tenant, merchant, mode, lock=True)
        active_ids = (
            _snapshot_query(db, tenant, merchant, mode)
            .filter(IfoodFinancialSnapshot.active.is_(True))
            .with_entities(IfoodFinancialSnapshot.id)
        )
        events = (
            db.query(IfoodFinancialEvent)
            .filter(
                IfoodFinancialEvent.tenant_id == tenant,
                IfoodFinancialEvent.snapshot_id.in_(active_ids),
                IfoodFinancialEvent.order_id == order_id,
            )
            .order_by(IfoodFinancialEvent.id)
            .all()
        )
        if not events:
            raise IfoodFinancialError(
                "Pedido não encontrado nos extratos desta loja.", status_code=404
            )
        previous = (
            _costs_query(db, tenant, merchant, mode)
            .filter(IfoodFinancialOrderCosts.order_id == order_id)
            .order_by(IfoodFinancialOrderCosts.version.desc())
            .first()
        )
        cost = IfoodFinancialOrderCosts(
            tenant_id=tenant,
            merchant_id=merchant,
            mode=mode,
            order_id=order_id,
            version=previous.version + 1 if previous else 1,
            **amounts,
            source_note=note.strip(),
            actor_id=actor,
        )
        db.add(cost)
        db.flush()
        snapshots = {event.snapshot_id for event in events}
        unallocated = (
            db.query(IfoodFinancialEvent.id)
            .filter(
                IfoodFinancialEvent.tenant_id == tenant,
                IfoodFinancialEvent.snapshot_id.in_(snapshots),
                IfoodFinancialEvent.order_id.is_(None),
            )
            .first()
            is not None
        )
        result = _order_view(
            order_id,
            events,
            cost,
            unallocated=unallocated,
            multiple_windows=len(snapshots) > 1,
        )
    except Exception:
        db.rollback()
        raise
    return {
        key: result[key]
        for key in ("order_id", "manual_costs", "contribution", "pending")
    }
