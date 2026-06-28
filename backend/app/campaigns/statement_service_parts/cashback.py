from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import or_ as sql_or_
from sqlalchemy.orm import Session

from app.campaigns.models import Campaign, CampaignExecution, CashbackTransaction
from app.campaigns.statement_service_parts.common import (
    _append_event,
    _campaign_fields,
    _date_in_range,
    _enum_value,
    _iso,
    _money,
)


def _add_cashback_events(
    db: Session,
    events: list[dict[str, Any]],
    *,
    tenant_id,
    customer_id: int,
    campaign_map: dict[int, Campaign],
    start_dt: datetime | None,
    end_dt: datetime | None,
) -> None:
    transactions = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
        )
        .all()
    )
    execution_ids = [
        int(tx.source_id)
        for tx in transactions
        if tx.source_id and _enum_value(tx.source_type) == "campaign"
    ]
    execution_map: dict[int, CampaignExecution] = {}
    if execution_ids:
        executions = (
            db.query(CampaignExecution)
            .filter(
                CampaignExecution.tenant_id == tenant_id,
                CampaignExecution.id.in_(execution_ids),
            )
            .all()
        )
        execution_map = {int(execution.id): execution for execution in executions}

    for tx in transactions:
        if not _date_in_range(tx.created_at, start_dt, end_dt):
            continue
        amount = _money(tx.amount) or 0
        execution = execution_map.get(int(tx.source_id)) if tx.source_id else None
        campaign = campaign_map.get(int(execution.campaign_id)) if execution else None
        source_type = _enum_value(tx.source_type)
        reward_meta = dict(execution.reward_meta or {}) if execution else {}
        try:
            venda_id = int(reward_meta.get("venda_id") or 0) or None
        except (TypeError, ValueError):
            venda_id = None
        if (
            venda_id is None
            and amount < 0
            and tx.source_id
            and source_type in {"manual", "redemption"}
        ):
            venda_id = int(tx.source_id)
        tx_type = tx.tx_type or ("credit" if amount >= 0 else "debit")
        title = "Cashback creditado" if amount >= 0 else "Cashback debitado"
        if tx_type == "expired":
            title = "Cashback expirado"
        elif source_type == "reversal":
            title = "Cashback estornado"

        _append_event(
            events,
            {
                "id": f"cashback:{tx.id}",
                "data": _iso(tx.created_at),
                "categoria": "cashback",
                "tipo": tx_type,
                "direcao": "credito" if amount >= 0 else "debito",
                "titulo": title,
                "descricao": tx.description,
                "valor": amount,
                "venda_id": venda_id,
                "status": "expirado" if tx_type == "expired" else "registrado",
                "origem": source_type,
                "metadata": {
                    "transaction_id": int(tx.id),
                    "source_id": int(tx.source_id) if tx.source_id else None,
                    "source_type": source_type,
                    "expires_at": _iso(tx.expires_at),
                    "reward_meta": reward_meta,
                },
                **_campaign_fields(campaign),
            },
        )


def _current_cashback_balance(db: Session, *, tenant_id, customer_id: int) -> float:
    now = datetime.now(timezone.utc)
    total = (
        db.query(CashbackTransaction.amount)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            sql_or_(
                CashbackTransaction.expires_at.is_(None),
                CashbackTransaction.expires_at > now,
                CashbackTransaction.tx_type != "credit",
            ),
        )
        .all()
    )
    saldo = sum((Decimal(str(row[0] or 0)) for row in total), Decimal("0.00"))
    return float(saldo.quantize(Decimal("0.01")))
