from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import or_ as sql_or
from sqlalchemy.orm import Session

from app.campaigns.loyalty_service import summarize_loyalty_balances_for_customer
from app.campaigns.models import (
    Campaign,
    CampaignExecution,
    CashbackTransaction,
    Coupon,
    CouponRedemption,
    CouponStatusEnum,
    CustomerRankHistory,
    LoyaltyStamp,
)
from app.models import Cliente
from app.vendas_models import Venda


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", str(value))


def _money(value: Any) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _start_of_day(value: date | None) -> datetime | None:
    return datetime.combine(value, time.min) if value else None


def _end_of_day(value: date | None) -> datetime | None:
    return datetime.combine(value, time.max) if value else None


def _date_in_range(value: datetime | None, start: datetime | None, end: datetime | None) -> bool:
    if value is None:
        return False
    if value.tzinfo is not None:
        if start is not None and start.tzinfo is None:
            start = start.replace(tzinfo=value.tzinfo)
        if end is not None and end.tzinfo is None:
            end = end.replace(tzinfo=value.tzinfo)
    elif value.tzinfo is None:
        if start is not None and start.tzinfo is not None:
            start = start.replace(tzinfo=None)
        if end is not None and end.tzinfo is not None:
            end = end.replace(tzinfo=None)
    if start and value < start:
        return False
    if end and value > end:
        return False
    return True


def _coupon_value(coupon: Coupon) -> float | None:
    if coupon.discount_value is not None:
        return _money(coupon.discount_value)
    if coupon.discount_percent is not None:
        return float(coupon.discount_percent)
    return None


def _coupon_value_label(coupon: Coupon) -> str | None:
    if coupon.discount_value is not None:
        return "valor"
    if coupon.discount_percent is not None:
        return "percentual"
    return None


def _consumed_stamps_from_meta(meta: dict[str, Any] | None) -> int:
    data = dict(meta or {})
    consumed = data.get("consumed_stamps")
    if consumed is None:
        consumed = data.get("stamps_to_complete_snapshot")
    try:
        return max(int(consumed or 0), 0)
    except (TypeError, ValueError):
        return 0


def _append_event(events: list[dict[str, Any]], event: dict[str, Any]) -> None:
    event.setdefault("valor", None)
    event.setdefault("quantidade", None)
    event.setdefault("saldo_carimbos", None)
    event.setdefault("saldo_cashback", None)
    event.setdefault("campanha_id", None)
    event.setdefault("campanha_nome", None)
    event.setdefault("campanha_tipo", None)
    event.setdefault("venda_id", None)
    event.setdefault("numero_venda", None)
    event.setdefault("cupom_id", None)
    event.setdefault("cupom_codigo", None)
    event.setdefault("status", None)
    event.setdefault("metadata", {})
    events.append(event)


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


def _sort_weight(categoria: str | None, tipo: str | None) -> int:
    if categoria == "carimbo" and tipo == "credito":
        return 10
    if categoria == "carimbo" and tipo == "conversao":
        return 20
    if categoria == "cupom" and tipo == "gerado":
        return 30
    if categoria == "cashback":
        return 40
    if categoria == "cupom":
        return 50
    if categoria == "carimbo":
        return 60
    return 90


def _campaign_fields(campaign: Campaign | None) -> dict[str, Any]:
    return {
        "campanha_id": int(campaign.id) if campaign else None,
        "campanha_nome": campaign.name if campaign else None,
        "campanha_tipo": _enum_value(campaign.campaign_type) if campaign else None,
    }


def _add_loyalty_stamp_events(
    db: Session,
    events: list[dict[str, Any]],
    *,
    tenant_id,
    customer_id: int,
    campaign_map: dict[int, Campaign],
    start_dt: datetime | None,
    end_dt: datetime | None,
) -> None:
    stamps = (
        db.query(LoyaltyStamp)
        .filter(
            LoyaltyStamp.tenant_id == tenant_id,
            LoyaltyStamp.customer_id == customer_id,
        )
        .all()
    )
    for stamp in stamps:
        campaign = campaign_map.get(int(stamp.campaign_id))
        if _date_in_range(stamp.created_at, start_dt, end_dt):
            _append_event(
                events,
                {
                    "id": f"stamp:{stamp.id}:created",
                    "data": _iso(stamp.created_at),
                    "categoria": "carimbo",
                    "tipo": "credito",
                    "direcao": "credito",
                    "titulo": "Carimbo gerado",
                    "descricao": (
                        stamp.notes
                        or (
                            "Carimbo manual"
                            if stamp.is_manual
                            else f"Carimbo gerado pela venda #{stamp.venda_id}"
                        )
                    ),
                    "quantidade": 1,
                    "venda_id": int(stamp.venda_id) if stamp.venda_id else None,
                    "status": "estornado" if stamp.voided_at else "ativo",
                    "origem": "manual" if stamp.is_manual else "venda",
                    "metadata": {"stamp_id": int(stamp.id), "stamp_index": int(stamp.stamp_index or 1)},
                    **_campaign_fields(campaign),
                },
            )
        if stamp.voided_at and _date_in_range(stamp.voided_at, start_dt, end_dt):
            _append_event(
                events,
                {
                    "id": f"stamp:{stamp.id}:voided",
                    "data": _iso(stamp.voided_at),
                    "categoria": "carimbo",
                    "tipo": "estorno",
                    "direcao": "debito",
                    "titulo": "Carimbo estornado",
                    "descricao": stamp.notes or "Carimbo estornado",
                    "quantidade": -1,
                    "venda_id": int(stamp.venda_id) if stamp.venda_id else None,
                    "status": "estornado",
                    "origem": "cancelamento" if stamp.venda_id else "manual",
                    "metadata": {"stamp_id": int(stamp.id), "stamp_index": int(stamp.stamp_index or 1)},
                    **_campaign_fields(campaign),
                },
            )


def _load_coupon_redemptions_by_coupon(
    db: Session,
    *,
    tenant_id,
    customer_id: int,
) -> dict[int, list[CouponRedemption]]:
    redemptions = (
        db.query(CouponRedemption)
        .filter(
            CouponRedemption.tenant_id == tenant_id,
            CouponRedemption.customer_id == customer_id,
        )
        .all()
    )
    grouped: dict[int, list[CouponRedemption]] = {}
    for redemption in redemptions:
        grouped.setdefault(int(redemption.coupon_id), []).append(redemption)
    return grouped


def _add_coupon_events(
    db: Session,
    events: list[dict[str, Any]],
    *,
    tenant_id,
    customer_id: int,
    campaign_map: dict[int, Campaign],
    redemptions_by_coupon: dict[int, list[CouponRedemption]],
    start_dt: datetime | None,
    end_dt: datetime | None,
    include_coupon_events: bool,
    include_stamp_conversion_events: bool,
) -> None:
    coupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.customer_id == customer_id,
        )
        .all()
    )
    for coupon in coupons:
        campaign = campaign_map.get(int(coupon.campaign_id)) if coupon.campaign_id else None
        meta = dict(coupon.meta or {})
        consumed_stamps = _consumed_stamps_from_meta(meta)
        coupon_redemptions = redemptions_by_coupon.get(int(coupon.id), [])

        if include_stamp_conversion_events and consumed_stamps > 0 and _date_in_range(coupon.created_at, start_dt, end_dt):
            _append_event(
                events,
                {
                    "id": f"coupon:{coupon.id}:stamps-consumed",
                    "data": _iso(coupon.created_at),
                    "categoria": "carimbo",
                    "tipo": "conversao",
                    "direcao": "debito",
                    "titulo": "Carimbos convertidos em cupom",
                    "descricao": f"{consumed_stamps} carimbo(s) usados para gerar o cupom {coupon.code}.",
                    "quantidade": -consumed_stamps,
                    "cupom_id": int(coupon.id),
                    "cupom_codigo": coupon.code,
                    "status": _enum_value(coupon.status),
                    "origem": "fidelidade",
                    "metadata": {"coupon_meta": meta},
                    **_campaign_fields(campaign),
                },
            )

        if include_coupon_events and _date_in_range(coupon.created_at, start_dt, end_dt):
            _append_event(
                events,
                {
                    "id": f"coupon:{coupon.id}:created",
                    "data": _iso(coupon.created_at),
                    "categoria": "cupom",
                    "tipo": "gerado",
                    "direcao": "credito",
                    "titulo": "Cupom gerado",
                    "descricao": f"Cupom {coupon.code} gerado.",
                    "valor": _coupon_value(coupon),
                    "cupom_id": int(coupon.id),
                    "cupom_codigo": coupon.code,
                    "status": _enum_value(coupon.status),
                    "origem": "campanha" if coupon.campaign_id else "manual",
                    "metadata": {
                        "coupon_type": _enum_value(coupon.coupon_type),
                        "valor_tipo": _coupon_value_label(coupon),
                        "valid_until": _iso(coupon.valid_until),
                        "min_purchase_value": _money(coupon.min_purchase_value),
                        "coupon_meta": meta,
                    },
                    **_campaign_fields(campaign),
                },
            )

        for redemption in coupon_redemptions:
            if include_coupon_events and _date_in_range(redemption.redeemed_at, start_dt, end_dt):
                _append_event(
                    events,
                    {
                        "id": f"coupon-redemption:{redemption.id}:redeemed",
                        "data": _iso(redemption.redeemed_at),
                        "categoria": "cupom",
                        "tipo": "uso",
                        "direcao": "debito",
                        "titulo": "Cupom usado",
                        "descricao": f"Cupom {coupon.code} usado em venda.",
                        "valor": -abs(_money(redemption.discount_applied) or 0),
                        "venda_id": int(redemption.venda_id) if redemption.venda_id else None,
                        "cupom_id": int(coupon.id),
                        "cupom_codigo": coupon.code,
                        "status": "estornado" if redemption.voided_at else "usado",
                        "origem": "venda",
                        "metadata": {"redemption_id": int(redemption.id)},
                        **_campaign_fields(campaign),
                    },
                )

            if redemption.voided_at and include_coupon_events and _date_in_range(redemption.voided_at, start_dt, end_dt):
                _append_event(
                    events,
                    {
                        "id": f"coupon-redemption:{redemption.id}:voided",
                        "data": _iso(redemption.voided_at),
                        "categoria": "cupom",
                        "tipo": "estorno",
                        "direcao": "credito",
                        "titulo": "Uso de cupom estornado",
                        "descricao": redemption.voided_reason or f"Uso do cupom {coupon.code} estornado.",
                        "valor": abs(_money(redemption.discount_applied) or 0),
                        "venda_id": int(redemption.venda_id) if redemption.venda_id else None,
                        "cupom_id": int(coupon.id),
                        "cupom_codigo": coupon.code,
                        "status": "estornado",
                        "origem": "cancelamento",
                        "metadata": {"redemption_id": int(redemption.id)},
                        **_campaign_fields(campaign),
                    },
                )

        voided_at_raw = meta.get("voided_at") or meta.get("revoked_at")
        voided_at = _parse_datetime(voided_at_raw)
        if (
            coupon.status == CouponStatusEnum.voided
            and voided_at
            and _date_in_range(voided_at, start_dt, end_dt)
            and not coupon_redemptions
        ):
            if include_coupon_events:
                _append_event(
                    events,
                    {
                        "id": f"coupon:{coupon.id}:voided",
                        "data": _iso(voided_at),
                        "categoria": "cupom",
                        "tipo": "anulacao",
                        "direcao": "debito",
                        "titulo": "Cupom anulado",
                        "descricao": meta.get("voided_reason") or f"Cupom {coupon.code} anulado.",
                        "valor": -abs(_coupon_value(coupon) or 0),
                        "cupom_id": int(coupon.id),
                        "cupom_codigo": coupon.code,
                        "status": "voided",
                        "origem": "manual",
                        "metadata": {"coupon_meta": meta},
                        **_campaign_fields(campaign),
                    },
                )
            if include_stamp_conversion_events and consumed_stamps > 0:
                _append_event(
                    events,
                    {
                        "id": f"coupon:{coupon.id}:stamps-restored",
                        "data": _iso(voided_at),
                        "categoria": "carimbo",
                        "tipo": "restauracao",
                        "direcao": "credito",
                        "titulo": "Carimbos restaurados por cupom anulado",
                        "descricao": f"{consumed_stamps} carimbo(s) restaurados do cupom {coupon.code}.",
                        "quantidade": consumed_stamps,
                        "cupom_id": int(coupon.id),
                        "cupom_codigo": coupon.code,
                        "status": "restaurado",
                        "origem": "anulacao_cupom",
                        "metadata": {"coupon_meta": meta},
                        **_campaign_fields(campaign),
                    },
                )


def _add_loyalty_execution_events(
    db: Session,
    events: list[dict[str, Any]],
    *,
    tenant_id,
    customer_id: int,
    campaign_map: dict[int, Campaign],
    start_dt: datetime | None,
    end_dt: datetime | None,
) -> None:
    executions = (
        db.query(CampaignExecution)
        .filter(
            CampaignExecution.tenant_id == tenant_id,
            CampaignExecution.customer_id == customer_id,
        )
        .all()
    )
    for execution in executions:
        campaign = campaign_map.get(int(execution.campaign_id))
        meta = dict(execution.reward_meta or {})
        consumed_stamps = _consumed_stamps_from_meta(meta)
        reward_type = str(execution.reward_type or "")
        is_coupon_reward = reward_type.startswith("coupon")

        if consumed_stamps > 0 and not is_coupon_reward and _date_in_range(execution.created_at, start_dt, end_dt):
            _append_event(
                events,
                {
                    "id": f"execution:{execution.id}:stamps-consumed",
                    "data": _iso(execution.created_at),
                    "categoria": "carimbo",
                    "tipo": "conversao",
                    "direcao": "debito",
                    "titulo": "Carimbos convertidos em recompensa",
                    "descricao": f"{consumed_stamps} carimbo(s) convertidos em {reward_type}.",
                    "quantidade": -consumed_stamps,
                    "status": "convertido",
                    "origem": "fidelidade",
                    "metadata": {"execution_id": int(execution.id), "reward_meta": meta},
                    **_campaign_fields(campaign),
                },
            )

        revoked_at = _parse_datetime(meta.get("revoked_at"))
        if meta.get("revoked_after_use") and revoked_at and _date_in_range(revoked_at, start_dt, end_dt):
            restored = _consumed_stamps_from_meta(
                {"consumed_stamps": meta.get("original_consumed_stamps")}
            )
            if restored > 0:
                _append_event(
                    events,
                    {
                        "id": f"execution:{execution.id}:stamps-restored-after-use",
                        "data": _iso(revoked_at),
                        "categoria": "carimbo",
                        "tipo": "restauracao",
                        "direcao": "credito",
                        "titulo": "Carimbos restaurados apos estorno de cupom usado",
                        "descricao": meta.get("revoked_reason") or "Recompensa de fidelidade estornada.",
                        "quantidade": restored,
                        "status": "restaurado",
                        "origem": "cancelamento",
                        "metadata": {"execution_id": int(execution.id), "reward_meta": meta},
                        **_campaign_fields(campaign),
                    },
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
        if venda_id is None and amount < 0 and tx.source_id and source_type in {"manual", "redemption"}:
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
        {
            int(event["venda_id"])
            for event in events
            if event.get("venda_id")
        }
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


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
