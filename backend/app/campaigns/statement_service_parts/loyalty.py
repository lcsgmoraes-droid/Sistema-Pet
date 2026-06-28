from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.campaigns.models import Campaign, CampaignExecution, LoyaltyStamp
from app.campaigns.statement_service_parts.common import (
    _append_event,
    _campaign_fields,
    _consumed_stamps_from_meta,
    _date_in_range,
    _iso,
    _parse_datetime,
)


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
                    "metadata": {
                        "stamp_id": int(stamp.id),
                        "stamp_index": int(stamp.stamp_index or 1),
                    },
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
                    "metadata": {
                        "stamp_id": int(stamp.id),
                        "stamp_index": int(stamp.stamp_index or 1),
                    },
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

        if (
            consumed_stamps > 0
            and not is_coupon_reward
            and _date_in_range(execution.created_at, start_dt, end_dt)
        ):
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
                    "metadata": {
                        "execution_id": int(execution.id),
                        "reward_meta": meta,
                    },
                    **_campaign_fields(campaign),
                },
            )

        revoked_at = _parse_datetime(meta.get("revoked_at"))
        if (
            meta.get("revoked_after_use")
            and revoked_at
            and _date_in_range(revoked_at, start_dt, end_dt)
        ):
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
                        "descricao": meta.get("revoked_reason")
                        or "Recompensa de fidelidade estornada.",
                        "quantidade": restored,
                        "status": "restaurado",
                        "origem": "cancelamento",
                        "metadata": {
                            "execution_id": int(execution.id),
                            "reward_meta": meta,
                        },
                        **_campaign_fields(campaign),
                    },
                )
