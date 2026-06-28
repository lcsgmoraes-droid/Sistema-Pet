from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.campaigns.loyalty_service import summarize_loyalty_balances_for_customer
from app.campaigns.models import Campaign
from app.campaigns.statement_service_parts.cashback import (
    _add_cashback_events,
    _current_cashback_balance,
)
from app.campaigns.statement_service_parts.common import (
    _end_of_day,
    _sort_weight,
    _start_of_day,
)
from app.campaigns.statement_service_parts.coupons import (
    _add_coupon_events,
    _load_coupon_redemptions_by_coupon,
)
from app.campaigns.statement_service_parts.loyalty import (
    _add_loyalty_execution_events,
    _add_loyalty_stamp_events,
)
from app.campaigns.statement_service_parts.ranking import (
    _add_ranking_events,
    _apply_running_balances,
    _enrich_sales,
)
from app.models import Cliente


def build_campaign_customer_statement(
    db: Session,
    *,
    tenant_id,
    customer_id: int,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    tipo: str | None = None,
    limit: int = 300,
) -> dict[str, Any]:
    start_dt = _start_of_day(data_inicio)
    end_dt = _end_of_day(data_fim)
    tipo_normalizado = (tipo or "todos").strip().lower()
    allowed_tipo = {"todos", "carimbos", "cashback", "cupons", "ranking"}
    if tipo_normalizado not in allowed_tipo:
        tipo_normalizado = "todos"

    cliente = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.id == customer_id)
        .first()
    )

    campaigns = db.query(Campaign).filter(Campaign.tenant_id == tenant_id).all()
    campaign_map = {int(campaign.id): campaign for campaign in campaigns}
    events: list[dict[str, Any]] = []

    if tipo_normalizado in {"todos", "carimbos"}:
        _add_loyalty_stamp_events(
            db,
            events,
            tenant_id=tenant_id,
            customer_id=customer_id,
            campaign_map=campaign_map,
            start_dt=start_dt,
            end_dt=end_dt,
        )

    coupon_redemptions_by_coupon = _load_coupon_redemptions_by_coupon(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
    )
    if tipo_normalizado in {"todos", "cupons", "carimbos"}:
        _add_coupon_events(
            db,
            events,
            tenant_id=tenant_id,
            customer_id=customer_id,
            campaign_map=campaign_map,
            redemptions_by_coupon=coupon_redemptions_by_coupon,
            start_dt=start_dt,
            end_dt=end_dt,
            include_coupon_events=tipo_normalizado in {"todos", "cupons"},
            include_stamp_conversion_events=tipo_normalizado in {"todos", "carimbos"},
        )

    if tipo_normalizado in {"todos", "carimbos"}:
        _add_loyalty_execution_events(
            db,
            events,
            tenant_id=tenant_id,
            customer_id=customer_id,
            campaign_map=campaign_map,
            start_dt=start_dt,
            end_dt=end_dt,
        )

    if tipo_normalizado in {"todos", "cashback"}:
        _add_cashback_events(
            db,
            events,
            tenant_id=tenant_id,
            customer_id=customer_id,
            campaign_map=campaign_map,
            start_dt=start_dt,
            end_dt=end_dt,
        )

    if tipo_normalizado in {"todos", "ranking"}:
        _add_ranking_events(
            db,
            events,
            tenant_id=tenant_id,
            customer_id=customer_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )

    events.sort(
        key=lambda item: (
            item.get("data") or "",
            _sort_weight(item.get("categoria"), item.get("tipo")),
            item.get("id") or "",
        )
    )
    _enrich_sales(db, events, tenant_id=tenant_id)
    _apply_running_balances(events)

    events_desc = list(reversed(events))
    if limit > 0:
        events_desc = events_desc[:limit]

    loyalty_summary = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
    )
    saldo_cashback = _current_cashback_balance(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    return {
        "customer_id": customer_id,
        "cliente_nome": cliente.nome if cliente else None,
        "filtros": {
            "tipo": tipo_normalizado,
            "data_inicio": data_inicio.isoformat() if data_inicio else None,
            "data_fim": data_fim.isoformat() if data_fim else None,
            "limit": limit,
        },
        "saldo_atual": {
            "cashback": saldo_cashback,
            "carimbos_disponiveis": loyalty_summary["total_carimbos"],
            "carimbos_brutos": loyalty_summary["total_carimbos_brutos"],
            "carimbos_comprometidos": loyalty_summary["carimbos_comprometidos_total"],
            "carimbos_convertidos": loyalty_summary["carimbos_convertidos"],
            "carimbos_em_debito": loyalty_summary["carimbos_em_debito"],
            "ciclos_concluidos": loyalty_summary["ciclos_concluidos"],
        },
        "eventos": events_desc,
    }
