"""Reconcile provider evidence by documented IDs, never by amount proximity.

All methods are flush-only. No sales, stock, bank or accounting writes occur.
"""

import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json
import re

from app.ifood_financial_models import IfoodFinancialEvent, IfoodFinancialSnapshot
from app.ifood_payout_models import IfoodPayoutSnapshot
from app.integrations.ifood.financial import (
    MODE,
    IfoodFinancialError,
    _actor,
    _code,
    _date,
    _iso,
    _money,
    _scope,
    _text,
)


def payout_period(begin, end, basis="calculation"):
    begin, end = _date(begin), _date(end)
    if basis not in {"calculation", "payment"}:
        raise IfoodFinancialError("Escolha apuração ou pagamento como base do período.")
    if end < begin or (end - begin).days > 89:
        raise IfoodFinancialError("Consulte de 1 a 90 dias, incluindo início e fim.")
    return begin, end


def competence_period(competence):
    if not isinstance(competence, str) or not re.fullmatch(
        r"\d{4}-(0[1-9]|1[0-2])", competence
    ):
        raise IfoodFinancialError("Competência inválida; use AAAA-MM.")
    try:
        year, month = map(int, competence.split("-"))
        return date(year, month, 1), date(
            year, month, calendar.monthrange(year, month)[1]
        )
    except ValueError as exc:
        raise IfoodFinancialError("Competência inválida.") from exc


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise IfoodFinancialError("Identificador de título inválido.")
    return value


def _settlements(payload, merchant, begin, end, basis):
    if isinstance(payload, list) and len(payload) == 1:
        payload = payload[0]
    if not isinstance(payload, dict) or payload.get("merchantId") != merchant:
        raise IfoodFinancialError("Repasse sem identificação da loja correta.")
    consolidated = payload.get("consolidatedMerchants")
    if consolidated is not None and (
        not isinstance(consolidated, list) or any(m != merchant for m in consolidated)
    ):
        raise IfoodFinancialError(
            "Repasse consolidado contém outra loja ou identificação não comprovada."
        )
    if _date(payload.get("beginDate")) != begin or _date(payload.get("endDate")) != end:
        raise IfoodFinancialError("O período retornado difere da consulta de repasses.")
    entries = payload.get("settlements")
    if not isinstance(entries, list) or len(entries) > 10000:
        raise IfoodFinancialError("Lista de repasses incompleta ou excessiva.")
    titles = []
    seen = set()

    def append(raw, period=None):
        if not isinstance(raw, dict):
            raise IfoodFinancialError("Título financeiro inválido.")
        title_id = _identifier(raw.get("id"))
        if title_id in seen:
            # Preserve legitimate titles; never collapse repeated/conflicting IDs.
            raise IfoodFinancialError(
                "Título repetido na resposta; conferir a consulta no iFood."
            )
        seen.add(title_id)
        payment = raw.get("paymentDate")
        payment = str(_date(payment)) if payment is not None else None
        if basis == "payment" and (
            payment is None or not begin <= _date(payment) <= end
        ):
            raise IfoodFinancialError("Título fora do período de pagamento consultado.")
        titles.append(
            {
                "id": title_id,
                "title_type": _code(raw.get("type")),
                "provider_status": _code(raw.get("status")),
                "amount": _text(_money(raw.get("amount"))),
                "payment_date": payment,
                "calculation_period": period,
            }
        )

    for entry in entries:
        if not isinstance(entry, dict):
            raise IfoodFinancialError("Grupo de repasses inválido.")
        if "closingItems" in entry:
            pb, pe = (
                _date(entry.get("startDateCalculation")),
                _date(entry.get("endDateCalculation")),
            )
            if (
                pe < pb
                or (pe - pb).days > 89
                or (basis == "calculation" and (pb < begin or pe > end))
            ):
                raise IfoodFinancialError(
                    "Apuração do repasse fora da janela consultada."
                )
            if not isinstance(entry["closingItems"], list):
                raise IfoodFinancialError("Grupo de repasses sem títulos completos.")
            for raw in entry["closingItems"]:
                append(raw, {"begin": str(pb), "end": str(pe)})
        else:
            append(entry)
        if len(titles) > 10000:
            raise IfoodFinancialError("Consulta excedeu o limite de títulos.")
    return {
        "balance": _text(_money(payload.get("balance"), nullable=True)),
        "titles": titles,
    }


def _query(db, tenant, merchant, mode):
    return db.query(IfoodPayoutSnapshot).filter(
        IfoodPayoutSnapshot.tenant_id == tenant,
        IfoodPayoutSnapshot.merchant_id == merchant,
        IfoodPayoutSnapshot.mode == mode,
    )


def _persist(
    db, tenant, merchant, mode, kind, basis, begin, end, evidence, actor, source
):
    if source not in {"synthetic", "ifood"}:
        raise IfoodFinancialError("Origem de evidência financeira inválida.")
    _scope(db, tenant, merchant, mode, lock=True)
    digest = sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    previous = (
        _query(db, tenant, merchant, mode)
        .filter_by(
            kind=kind,
            basis=basis,
            begin_date=begin,
            end_date=end,
            active=True,
        )
        .first()
    )
    if previous and previous.payload_hash == digest and previous.source == source:
        return previous
    # Another window may include the same title. It is kept as independent
    # evidence, never accumulated into a cross-window total.
    revision = previous.revision + 1 if previous else 1
    if previous:
        previous.active = False
        db.flush()
    snapshot = IfoodPayoutSnapshot(
        tenant_id=tenant,
        merchant_id=merchant,
        mode=mode,
        kind=kind,
        basis=basis,
        begin_date=begin,
        end_date=end,
        revision=revision,
        active=True,
        source=source,
        payload_hash=digest,
        evidence=evidence,
        actor_id=_actor(actor),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def import_settlements(
    db,
    tenant_id,
    merchant_id,
    begin_date,
    end_date,
    payload,
    actor_id,
    basis="calculation",
    mode=MODE,
    source="ifood",
):
    begin, end = payout_period(begin_date, end_date, basis)
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode)
    evidence = _settlements(payload, merchant, begin, end, basis)
    _persist(
        db,
        tenant,
        merchant,
        mode,
        "settlements",
        basis,
        begin,
        end,
        evidence,
        actor_id,
        source,
    )
    return get_payout_report(db, tenant, merchant, begin, end, basis, mode)


def import_statement(
    db, tenant_id, merchant_id, competence, parsed, actor_id, mode=MODE, source="ifood"
):
    begin, end = competence_period(competence)
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode)
    if (
        not isinstance(parsed, dict)
        or parsed.get("merchant_id") != merchant
        or parsed.get("competence") != competence
    ):
        raise IfoodFinancialError(
            "Arquivo de conciliação não corresponde à loja e competência."
        )
    rows = parsed.get("rows")
    if (
        not isinstance(rows, list)
        or len(rows) > 100000
        or parsed.get("row_count") != len(rows)
    ):
        raise IfoodFinancialError("Arquivo de conciliação incompleto.")
    clean = []
    for pos, row in enumerate(rows, 1):
        if (
            not isinstance(row, dict)
            or row.get("position") != pos
            or type(row.get("has_transfer_impact")) is not bool
        ):
            raise IfoodFinancialError("Linha de conciliação inválida.")
        item = {
            "position": pos,
            "amount": _text(_money(row.get("amount"))),
            "has_transfer_impact": row["has_transfer_impact"],
            "transaction_amount": _text(
                _money(row.get("transaction_amount"), nullable=True)
            ),
            "transaction_open": row.get("transaction_open") is True,
        }
        for key in ("title_id", "balance_id", "order_id"):
            item[key] = _identifier(row[key]) if row.get(key) is not None else None
        for key in ("period_begin", "period_end", "expected_payment_date"):
            item[key] = str(_date(row[key])) if row.get(key) is not None else None
        if (
            item["period_begin"]
            and item["period_end"]
            and item["period_end"] < item["period_begin"]
        ):
            raise IfoodFinancialError("Período de conciliação inválido.")
        if (
            item["period_begin"]
            and item["period_end"]
            and (_date(item["period_end"]) - _date(item["period_begin"])).days > 89
        ):
            raise IfoodFinancialError(
                "Apuração de conciliação excede a janela suportada."
            )
        clean.append(item)
    return _persist(
        db,
        tenant,
        merchant,
        mode,
        "statement",
        "competence",
        begin,
        end,
        {"competence": competence, "rows": clean},
        actor_id,
        source,
    )


def _months(begin, end):
    result = []
    current = begin.replace(day=1)
    while current <= end:
        result.append(current.strftime("%Y-%m"))
        if (current.year, current.month) == (end.year, end.month):
            break
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return result


def get_payout_report(
    db, tenant_id, merchant_id, begin_date, end_date, basis="calculation", mode=MODE
):
    begin, end = payout_period(begin_date, end_date, basis)
    tenant, merchant = _scope(db, tenant_id, merchant_id, mode)
    snapshot = (
        _query(db, tenant, merchant, mode)
        .filter_by(
            kind="settlements",
            basis=basis,
            begin_date=begin,
            end_date=end,
            active=True,
        )
        .first()
    )
    result = {
        "mode": mode,
        "merchant_id": merchant,
        "basis": basis,
        "begin_date": str(begin),
        "end_date": str(end),
        "imported": snapshot is not None,
        "metadata": None,
        "reported_balance": None,
        "titles": [],
        "unmatched_balances": [],
        "warnings": [
            "Conciliação do provedor não comprova recebimento bancário.",
            "Repasse, boleto e retenção são tipos distintos; não somar todos como receita.",
        ],
    }
    if snapshot is None:
        result["summary"] = {
            "titles_count": 0,
            "matched_titles": 0,
            "divergent_titles": 0,
            "pending_titles": 0,
            "totals_by_type": {},
        }
        return result
    result["metadata"] = {
        "source": snapshot.source,
        "revision": snapshot.revision,
        "retrieved_at": _iso(snapshot.created_at),
    }
    result["reported_balance"] = snapshot.evidence["balance"]
    statements = (
        _query(db, tenant, merchant, mode)
        .filter_by(kind="statement", active=True)
        .all()
    )
    # Source is part of the proof. Synthetic and official evidence never match.
    statements = [s for s in statements if s.source == snapshot.source]
    loaded_months = {s.evidence["competence"] for s in statements}
    rows = [
        (s.evidence["competence"], r) for s in statements for r in s.evidence["rows"]
    ]
    by_title, by_balance = defaultdict(list), defaultdict(list)
    for month, row in rows:
        if row["title_id"]:
            by_title[row["title_id"]].append((month, row))
        elif row["balance_id"]:
            by_balance[row["balance_id"]].append(row)
    for bid, entries in sorted(by_balance.items()):
        result["unmatched_balances"].append(
            {
                "balance_id": bid,
                "amount": _text(
                    sum(
                        (
                            _money(r["amount"])
                            for r in entries
                            if r["has_transfer_impact"]
                        ),
                        Decimal(0),
                    )
                ),
                "issues": [
                    "O iFood não informou a relação deste id_saldo com um título; vínculo pendente."
                ],
            }
        )
    events_snapshots = (
        db.query(IfoodFinancialSnapshot)
        .filter_by(
            tenant_id=tenant,
            merchant_id=merchant,
            mode=mode,
            active=True,
        )
        .all()
    )
    matching_source = (
        "synthetic" if snapshot.source == "synthetic" else "ifood_financial_events"
    )
    events_snapshots = [s for s in events_snapshots if s.source == matching_source]
    ids = [s.id for s in events_snapshots]
    events = (
        db.query(IfoodFinancialEvent)
        .filter(
            IfoodFinancialEvent.tenant_id == tenant,
            IfoodFinancialEvent.snapshot_id.in_(ids),
        )
        .all()
        if ids
        else []
    )
    event_windows = {
        (str(s.begin_date), str(s.end_date)): s.id for s in events_snapshots
    }
    snapshot_events = defaultdict(list)
    for event in events:
        snapshot_events[event.snapshot_id].append(event)
    totals = defaultdict(Decimal)
    for original in snapshot.evidence["titles"]:
        title = {
            **original,
            "statement_amount": None,
            "statement_lines_sum": None,
            "events_period_sum": None,
            "difference": None,
            "reconciliation_status": "pending",
            "bank_status": "not_checked",
            "link_method": None,
            "issues": [],
            "statement_row_count": 0,
            "event_count": 0,
            "reference_months": [],
        }
        totals[title["title_type"]] += _money(title["amount"])
        linked = by_title.get(title["id"], [])
        issues = title["issues"]
        if not linked:
            issues.append(
                "Arquivo sem título legado correspondente; não associar por valor ou data."
            )
        else:
            title["link_method"] = "legacy_title"
            title["reference_months"] = sorted({m for m, _ in linked})
            title["statement_row_count"] = len(linked)
            entries = [r for _, r in linked]
            declared = {
                _money(r["transaction_amount"])
                for r in entries
                if r["transaction_amount"] is not None
            }
            line_sum = sum(
                (_money(r["amount"]) for r in entries if r["has_transfer_impact"]),
                Decimal(0),
            )
            title["statement_lines_sum"] = _text(line_sum)
            if len(declared) == 1 and all(
                r["transaction_amount"] is not None and not r["transaction_open"]
                for r in entries
            ):
                title["statement_amount"] = _text(next(iter(declared)))
                title["difference"] = _text(_money(title["amount"]) - line_sum)
            else:
                issues.append(
                    "Total da transação ausente, aberto ou inconsistente no arquivo."
                )
            periods = {(r["period_begin"], r["period_end"]) for r in entries}
            expected = title["calculation_period"]
            if len(periods) != 1 or any(None in period for period in periods):
                issues.append("Apuração das linhas não está completa e inequívoca.")
                period_key = None
            else:
                period_key = next(iter(periods))
                if basis == "calculation" and (
                    _date(period_key[0]) < begin or _date(period_key[1]) > end
                ):
                    issues.append(
                        "Apuração do arquivo está fora da consulta de repasses."
                    )
                if expected and period_key != (expected["begin"], expected["end"]):
                    issues.append("Apuração do título diverge da apuração do arquivo.")
                elif expected is None:
                    title["calculation_period"] = {
                        "begin": period_key[0],
                        "end": period_key[1],
                    }
                expected_payments = {
                    r["expected_payment_date"]
                    for r in entries
                    if r["expected_payment_date"]
                }
                if title["payment_date"] and any(
                    p != title["payment_date"] for p in expected_payments
                ):
                    issues.append(
                        "Data de pagamento difere da previsão do arquivo; confira no iFood."
                    )
                required = set(_months(_date(period_key[0]), _date(period_key[1])))
                if not required <= loaded_months:
                    issues.append(
                        "Faltam competências para cobrir toda a apuração do título."
                    )
                if period_key not in event_windows:
                    issues.append("Consulte os eventos da janela exata desta apuração.")
                else:
                    matching = snapshot_events[event_windows[period_key]]
                    title["event_count"] = len(matching)
                    event_sum = sum(
                        (e.amount for e in matching if e.has_transfer_impact),
                        Decimal(0),
                    )
                    title["events_period_sum"] = _text(event_sum)
                    if any(
                        (
                            e.evidence.get("period", {}).get("beginDate"),
                            e.evidence.get("period", {}).get("endDate"),
                        )
                        != period_key
                        for e in matching
                    ):
                        issues.append(
                            "A janela contém eventos de subperíodos; confira a abrangência da apuração."
                        )
                    # This checks the whole period, not a guessed allocation of
                    # each event to one of several titles in that period.
                    period_rows = [
                        r
                        for _, r in rows
                        if (r["period_begin"], r["period_end"]) == period_key
                    ]
                    period_sum = sum(
                        (
                            _money(r["amount"])
                            for r in period_rows
                            if r["has_transfer_impact"]
                        ),
                        Decimal(0),
                    )
                    if event_sum != period_sum:
                        issues.append(
                            "Eventos e arquivo divergem no total da apuração."
                        )
            mismatched = title["statement_amount"] is not None and (
                _money(title["amount"]) != line_sum
                or _money(title["statement_amount"]) != line_sum
            )
            if mismatched:
                title["reconciliation_status"] = "different"
                issues.append(
                    "Valor do título, total declarado e soma das linhas divergem."
                )
            elif not issues:
                title["reconciliation_status"] = "matched"
        result["titles"].append(title)
    states = [t["reconciliation_status"] for t in result["titles"]]
    result["summary"] = {
        "titles_count": len(states),
        "matched_titles": states.count("matched"),
        "divergent_titles": states.count("different"),
        "pending_titles": states.count("pending"),
        "totals_by_type": {k: _text(v) for k, v in totals.items()},
    }
    if not states:
        result["warnings"].append(
            "O iFood retornou a consulta sem títulos; isso não confirma saldo liquidado."
        )
    return result
