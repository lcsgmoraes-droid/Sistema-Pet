from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.campaigns.models import CustomerRankHistory
from app.campaigns.statement_service_parts.common import (
    _append_event,
    _date_in_range,
    _enum_value,
    _iso,
    _money,
)
from app.vendas_models import Venda


def _add_ranking_events(
    db: Session,
    events: list[dict[str, Any]],
    *,
    tenant_id,
    customer_id: int,
    start_dt: datetime | None,
    end_dt: datetime | None,
) -> None:
    rows = (
        db.query(CustomerRankHistory)
        .filter(
            CustomerRankHistory.tenant_id == tenant_id,
            CustomerRankHistory.customer_id == customer_id,
        )
        .all()
    )
    for row in rows:
        if not _date_in_range(row.calculated_at, start_dt, end_dt):
            continue
        _append_event(
            events,
            {
                "id": f"rank:{row.id}",
                "data": _iso(row.calculated_at),
                "categoria": "ranking",
                "tipo": "snapshot",
                "direcao": "neutro",
                "titulo": "Ranking calculado",
                "descricao": f"Cliente ficou no nivel {_enum_value(row.rank_level)} no periodo {row.period}.",
                "valor": _money(row.total_spent),
                "status": _enum_value(row.rank_level),
                "origem": "ranking_mensal",
                "metadata": {
                    "rank_history_id": int(row.id),
                    "period": row.period,
                    "total_purchases": int(row.total_purchases or 0),
                    "active_months": int(row.active_months or 0),
                },
            },
        )


def _enrich_sales(db: Session, events: list[dict[str, Any]], *, tenant_id) -> None:
    venda_ids = sorted(
        {int(event["venda_id"]) for event in events if event.get("venda_id")}
    )
    if not venda_ids:
        return
    vendas = (
        db.query(Venda.id, Venda.numero_venda)
        .filter(Venda.tenant_id == tenant_id, Venda.id.in_(venda_ids))
        .all()
    )
    vendas_map = {int(venda_id): numero for venda_id, numero in vendas}
    for event in events:
        venda_id = event.get("venda_id")
        if venda_id:
            event["numero_venda"] = vendas_map.get(int(venda_id))


def _apply_running_balances(events: list[dict[str, Any]]) -> None:
    saldo_carimbos = 0
    saldo_cashback = Decimal("0.00")
    for event in events:
        if event.get("categoria") == "carimbo":
            saldo_carimbos += int(event.get("quantidade") or 0)
            event["saldo_carimbos"] = saldo_carimbos
        elif event.get("categoria") == "cashback":
            saldo_cashback += Decimal(str(event.get("valor") or 0))
            event["saldo_cashback"] = float(saldo_cashback.quantize(Decimal("0.01")))
