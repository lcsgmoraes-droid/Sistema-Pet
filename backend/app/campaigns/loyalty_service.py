from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.campaigns.coupon_service import create_coupon
from app.campaigns.models import (
    Campaign,
    CampaignExecution,
    CashbackSourceTypeEnum,
    CashbackTransaction,
    Coupon,
    CouponStatusEnum,
    LoyaltyStamp,
)
from app.campaigns.notification_service import enqueue_email
from app.models import Cliente

logger = logging.getLogger(__name__)


def calculate_loyalty_stamp_count(venda_total: Any, stamp_value: Any) -> int:
    sale_total = Decimal(str(venda_total or 0))
    step_value = Decimal(str(stamp_value or 0))
    if sale_total <= 0 or step_value <= 0:
        return 0
    return int(sale_total // step_value)


def build_loyalty_reward_refs(
    total_stamps: int,
    stamps_to_complete: int,
    intermediate_stamp: int | None = None,
) -> set[str]:
    refs: set[str] = set()

    if stamps_to_complete > 0:
        for cycle in range(1, (total_stamps // stamps_to_complete) + 1):
            refs.add(f"cycle-{cycle}")

    if intermediate_stamp and intermediate_stamp > 0:
        for mid_cycle in range(1, (total_stamps // intermediate_stamp) + 1):
            reached_stamps = mid_cycle * intermediate_stamp
            if stamps_to_complete > 0 and reached_stamps % stamps_to_complete == 0:
                continue
            refs.add(f"mid-{mid_cycle}")

    return refs


def calculate_loyalty_consumed_stamps(
    completed_cycles: int,
    stamps_to_complete: Any,
) -> int:
    cycles = max(int(completed_cycles or 0), 0)
    step_value = max(int(stamps_to_complete or 0), 0)
    if cycles <= 0 or step_value <= 0:
        return 0
    return cycles * step_value


def calculate_loyalty_available_stamps(
    total_stamps: int,
    completed_cycles: int,
    stamps_to_complete: Any,
) -> int:
    available = int(total_stamps or 0) - calculate_loyalty_consumed_stamps(
        completed_cycles,
        stamps_to_complete,
    )
    return max(available, 0)


def count_active_loyalty_stamps(
    db: Session,
    *,
    tenant_id,
    campaign_id: int,
    customer_id: int,
) -> int:
    total = (
        db.query(func.count(LoyaltyStamp.id))
        .filter(
            LoyaltyStamp.tenant_id == tenant_id,
            LoyaltyStamp.campaign_id == campaign_id,
            LoyaltyStamp.customer_id == customer_id,
            LoyaltyStamp.voided_at.is_(None),
        )
        .scalar()
    )
    return int(total or 0)


def count_loyalty_completed_cycles(
    db: Session,
    *,
    tenant_id,
    campaign_id: int,
    customer_id: int,
) -> int:
    total = (
        db.query(func.count(CampaignExecution.id))
        .filter(
            CampaignExecution.tenant_id == tenant_id,
            CampaignExecution.campaign_id == campaign_id,
            CampaignExecution.customer_id == customer_id,
            CampaignExecution.reference_period.like("cycle-%"),
        )
        .scalar()
    )
    return int(total or 0)


def get_loyalty_balance_for_campaign(
    db: Session,
    *,
    campaign: Campaign,
    customer_id: int,
) -> dict[str, int]:
    params = campaign.params or {}
    stamps_to_complete = int(params.get("stamps_to_complete", 10) or 0)
    total_stamps = count_active_loyalty_stamps(
        db,
        tenant_id=campaign.tenant_id,
        campaign_id=campaign.id,
        customer_id=customer_id,
    )
    completed_cycles = count_loyalty_completed_cycles(
        db,
        tenant_id=campaign.tenant_id,
        campaign_id=campaign.id,
        customer_id=customer_id,
    )
    consumed_total = calculate_loyalty_consumed_stamps(
        completed_cycles,
        stamps_to_complete,
    )
    available_stamps = calculate_loyalty_available_stamps(
        total_stamps,
        completed_cycles,
        stamps_to_complete,
    )

    return {
        "total_stamps": total_stamps,
        "completed_cycles": completed_cycles,
        "consumed_stamps": consumed_total,
        "converted_stamps": min(total_stamps, consumed_total),
        "available_stamps": available_stamps,
    }


def summarize_loyalty_balances_for_customer(
    db: Session,
    *,
    tenant_id,
    customer_id: int,
) -> dict[str, int]:
    stamp_rows = (
        db.query(
            LoyaltyStamp.campaign_id,
            func.count(LoyaltyStamp.id).label("total_stamps"),
        )
        .filter(
            LoyaltyStamp.tenant_id == tenant_id,
            LoyaltyStamp.customer_id == customer_id,
            LoyaltyStamp.voided_at.is_(None),
        )
        .group_by(LoyaltyStamp.campaign_id)
        .all()
    )
    if not stamp_rows:
        return {
            "total_carimbos": 0,
            "total_carimbos_brutos": 0,
            "carimbos_convertidos": 0,
            "ciclos_concluidos": 0,
        }

    campaign_ids = [int(row.campaign_id) for row in stamp_rows]
    campaigns = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.id.in_(campaign_ids),
        )
        .all()
    )
    campaign_map = {int(campaign.id): campaign for campaign in campaigns}

    total_raw = 0
    total_available = 0
    total_converted = 0
    total_cycles = 0

    for row in stamp_rows:
        campaign_id = int(row.campaign_id)
        raw_total = int(row.total_stamps or 0)
        total_raw += raw_total

        campaign = campaign_map.get(campaign_id)
        stamps_to_complete = int(((campaign.params if campaign else {}) or {}).get("stamps_to_complete", 10) or 0)
        completed_cycles = count_loyalty_completed_cycles(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            customer_id=customer_id,
        )
        total_cycles += completed_cycles
        total_converted += min(
            raw_total,
            calculate_loyalty_consumed_stamps(completed_cycles, stamps_to_complete),
        )
        total_available += calculate_loyalty_available_stamps(
            raw_total,
            completed_cycles,
            stamps_to_complete,
        )

    return {
        "total_carimbos": total_available,
        "total_carimbos_brutos": total_raw,
        "carimbos_convertidos": total_converted,
        "ciclos_concluidos": total_cycles,
    }


def build_consumed_loyalty_stamp_ids(
    stamps: list[LoyaltyStamp],
    *,
    completed_cycles: int,
    stamps_to_complete: Any,
) -> set[int]:
    active_stamps = sorted(
        [stamp for stamp in stamps if stamp.voided_at is None],
        key=lambda stamp: (stamp.created_at, stamp.id),
    )
    consumed_visible = min(
        len(active_stamps),
        calculate_loyalty_consumed_stamps(completed_cycles, stamps_to_complete),
    )
    return {
        int(stamp.id)
        for stamp in active_stamps[:consumed_visible]
    }


def sync_loyalty_stamps_for_sale(
    db: Session,
    *,
    campaign: Campaign,
    customer_id: int,
    venda_id: int,
    venda_total: Any,
    source_event_id: int | None = None,
    reason: str | None = None,
) -> dict[str, int]:
    params = campaign.params or {}
    stamp_value = params.get("min_purchase_value", 0) or 0
    expected_stamps = calculate_loyalty_stamp_count(venda_total, stamp_value)

    existing_auto_stamps = (
        db.query(LoyaltyStamp)
        .filter(
            LoyaltyStamp.tenant_id == campaign.tenant_id,
            LoyaltyStamp.campaign_id == campaign.id,
            LoyaltyStamp.customer_id == customer_id,
            LoyaltyStamp.venda_id == venda_id,
            LoyaltyStamp.is_manual.is_(False),
        )
        .order_by(LoyaltyStamp.stamp_index.asc(), LoyaltyStamp.id.asc())
        .all()
    )

    stamps_by_index = {
        int(stamp.stamp_index or 1): stamp
        for stamp in existing_auto_stamps
    }
    now = datetime.now(timezone.utc)
    added = 0
    reactivated = 0
    voided = 0

    for stamp_index in range(1, expected_stamps + 1):
        stamp = stamps_by_index.get(stamp_index)
        if stamp is None:
            db.add(
                LoyaltyStamp(
                    tenant_id=campaign.tenant_id,
                    customer_id=customer_id,
                    venda_id=venda_id,
                    campaign_id=campaign.id,
                    stamp_index=stamp_index,
                    is_manual=False,
                    notes=reason,
                )
            )
            added += 1
            continue

        if stamp.voided_at is not None:
            stamp.voided_at = None
            if reason:
                stamp.notes = _append_note(stamp.notes, f"Reativado: {reason}")
            reactivated += 1

    for stamp in existing_auto_stamps:
        stamp_index = int(stamp.stamp_index or 1)
        if stamp.voided_at is None and stamp_index > expected_stamps:
            stamp.voided_at = now
            if reason:
                stamp.notes = _append_note(stamp.notes, f"Estornado: {reason}")
            voided += 1

    db.flush()

    reward_sync = sync_loyalty_rewards_for_customer(
        db,
        campaign=campaign,
        customer_id=customer_id,
        source_event_id=source_event_id,
    )

    return {
        "expected_stamps": expected_stamps,
        "stamps_added": added,
        "stamps_reactivated": reactivated,
        "stamps_voided": voided,
        "total_stamps": reward_sync["total_stamps"],
        "available_stamps": reward_sync["available_stamps"],
        "converted_stamps": reward_sync["converted_stamps"],
        "awarded": reward_sync["awarded"],
        "revoked": reward_sync["revoked"],
    }


def sync_loyalty_rewards_for_customer(
    db: Session,
    *,
    campaign: Campaign,
    customer_id: int,
    source_event_id: int | None = None,
) -> dict[str, int]:
    params = campaign.params or {}
    stamps_to_complete = int(params.get("stamps_to_complete", 10) or 0)
    intermediate_stamp = int(params.get("intermediate_stamp") or 0)
    balance = get_loyalty_balance_for_campaign(
        db,
        campaign=campaign,
        customer_id=customer_id,
    )
    total_stamps = balance["total_stamps"]
    desired_refs: dict[str, dict[str, Any]] = {}

    if stamps_to_complete > 0 and _is_reward_configured(
        params.get("reward_type", "coupon"),
        params.get("reward_value", 0),
    ):
        for cycle in range(1, (total_stamps // stamps_to_complete) + 1):
            ref = f"cycle-{cycle}"
            desired_refs[ref] = {
                "reward_tp": params.get("reward_type", "coupon"),
                "reward_val": params.get("reward_value", 0),
                "prefix": "FIEL",
                "notif_msg": params.get(
                    "notification_message",
                    "Parabens! Seu cartao de fidelidade completou um ciclo. Recompensa: {code}",
                ),
            }

    if intermediate_stamp > 0 and _is_reward_configured(
        params.get("intermediate_reward_type", "coupon"),
        params.get("intermediate_reward_value", 0),
    ):
        for mid_cycle in range(1, (total_stamps // intermediate_stamp) + 1):
            reached_stamps = mid_cycle * intermediate_stamp
            if stamps_to_complete > 0 and reached_stamps % stamps_to_complete == 0:
                continue

            ref = f"mid-{mid_cycle}"
            desired_refs[ref] = {
                "reward_tp": params.get("intermediate_reward_type", "coupon"),
                "reward_val": params.get("intermediate_reward_value", 0),
                "prefix": "FIELMID",
                "notif_msg": params.get(
                    "notification_message_intermediate",
                    "Voce atingiu um marco da fidelidade. Recompensa: {code}",
                ),
            }

    existing_executions = (
        db.query(CampaignExecution)
        .filter(
            CampaignExecution.tenant_id == campaign.tenant_id,
            CampaignExecution.campaign_id == campaign.id,
            CampaignExecution.customer_id == customer_id,
        )
        .all()
    )
    existing_map = {
        execution.reference_period: execution
        for execution in existing_executions
        if _is_loyalty_ref(execution.reference_period)
    }

    awarded = 0
    revoked = 0

    for ref_period in _sort_loyalty_refs(desired_refs.keys()):
        if ref_period in existing_map:
            continue

        reward = desired_refs[ref_period]
        awarded += _give_loyalty_reward(
            db,
            campaign=campaign,
            customer_id=customer_id,
            ref_period=ref_period,
            reward_tp=reward["reward_tp"],
            reward_val=reward["reward_val"],
            source_event_id=source_event_id,
            prefix=reward["prefix"],
            notif_msg=reward["notif_msg"],
        )

    for ref_period, execution in existing_map.items():
        if ref_period in desired_refs:
            continue
        revoked += _revoke_loyalty_reward(
            db,
            campaign=campaign,
            execution=execution,
        )

    return {
        "total_stamps": total_stamps,
        "available_stamps": balance["available_stamps"],
        "converted_stamps": balance["converted_stamps"],
        "completed_cycles": balance["completed_cycles"],
        "awarded": awarded,
        "revoked": revoked,
    }


def void_loyalty_stamps_for_sale(
    db: Session,
    *,
    tenant_id,
    venda_id: int,
    reason: str | None = None,
) -> dict[str, int]:
    sale_campaigns = (
        db.query(LoyaltyStamp.campaign_id, LoyaltyStamp.customer_id)
        .filter(
            LoyaltyStamp.tenant_id == tenant_id,
            LoyaltyStamp.venda_id == venda_id,
            LoyaltyStamp.is_manual.is_(False),
        )
        .distinct()
        .all()
    )

    affected_campaigns = 0
    total_voided = 0
    total_revoked = 0

    for campaign_id, customer_id in sale_campaigns:
        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.tenant_id == tenant_id,
            )
            .first()
        )

        if campaign is None:
            active_stamps = (
                db.query(LoyaltyStamp)
                .filter(
                    LoyaltyStamp.tenant_id == tenant_id,
                    LoyaltyStamp.campaign_id == campaign_id,
                    LoyaltyStamp.customer_id == customer_id,
                    LoyaltyStamp.venda_id == venda_id,
                    LoyaltyStamp.is_manual.is_(False),
                    LoyaltyStamp.voided_at.is_(None),
                )
                .all()
            )
            if active_stamps:
                affected_campaigns += 1
                now = datetime.now(timezone.utc)
                for stamp in active_stamps:
                    stamp.voided_at = now
                    if reason:
                        stamp.notes = _append_note(stamp.notes, f"Estornado: {reason}")
                total_voided += len(active_stamps)
            continue

        result = sync_loyalty_stamps_for_sale(
            db,
            campaign=campaign,
            customer_id=int(customer_id),
            venda_id=venda_id,
            venda_total=0,
            source_event_id=None,
            reason=reason,
        )
        affected_campaigns += 1
        total_voided += result["stamps_voided"]
        total_revoked += result["revoked"]

    return {
        "affected_campaigns": affected_campaigns,
        "stamps_voided": total_voided,
        "rewards_revoked": total_revoked,
    }


def _give_loyalty_reward(
    db: Session,
    *,
    campaign: Campaign,
    customer_id: int,
    ref_period: str,
    reward_tp: str,
    reward_val: Any,
    source_event_id: int | None,
    prefix: str,
    notif_msg: str,
) -> int:
    existing = (
        db.query(CampaignExecution.id)
        .filter(
            CampaignExecution.tenant_id == campaign.tenant_id,
            CampaignExecution.campaign_id == campaign.id,
            CampaignExecution.customer_id == customer_id,
            CampaignExecution.reference_period == ref_period,
        )
        .first()
    )
    if existing:
        return 0

    cliente = db.query(Cliente).filter(Cliente.id == customer_id).first()
    reward_meta: dict[str, Any] = {}
    reward_value = Decimal(str(reward_val or 0)).quantize(Decimal("0.01"))
    reward_type = reward_tp
    code = None

    if reward_tp == "coupon":
        coupon = create_coupon(
            db,
            tenant_id=campaign.tenant_id,
            campaign=campaign,
            customer_id=customer_id,
            coupon_type="fixed",
            discount_value=reward_value,
            channel="all",
            valid_days=int((campaign.params or {}).get("coupon_days_valid") or 30),
            prefix=prefix,
            meta={"reference_period": ref_period},
        )
        code = coupon.code
        reward_meta = {"coupon_id": coupon.id, "coupon_code": code}
        reward_type = "coupon:fixed"
    elif reward_tp == "credit":
        tx = CashbackTransaction(
            tenant_id=campaign.tenant_id,
            customer_id=customer_id,
            amount=reward_value,
            source_type=CashbackSourceTypeEnum.campaign,
            source_id=None,
            description=f"Recompensa de fidelidade {campaign.name} ({ref_period})",
            tx_type="credit",
        )
        db.add(tx)
        db.flush()
        reward_meta = {"cashback_tx_id": tx.id}
        reward_type = "cashback"
        code = f"R$ {reward_value:.2f}"
    elif reward_tp == "brinde":
        reward_meta = {"tipo": "brinde", "reference_period": ref_period}
        reward_type = "brinde"
        code = "brinde"
    else:
        logger.warning(
            "[loyalty_service] Tipo de recompensa nao suportado: %s",
            reward_tp,
        )
        return 0

    execution = CampaignExecution(
        tenant_id=campaign.tenant_id,
        campaign_id=campaign.id,
        customer_id=customer_id,
        reference_period=ref_period,
        reward_type=reward_type,
        reward_value=reward_value,
        reward_meta=reward_meta,
        source_event_id=source_event_id,
    )
    db.add(execution)
    db.flush()

    cashback_tx_id = reward_meta.get("cashback_tx_id")
    if cashback_tx_id:
        cashback_tx = db.get(CashbackTransaction, cashback_tx_id)
        if cashback_tx is not None:
            cashback_tx.source_id = execution.id

    if cliente and cliente.email:
        if reward_tp == "credit":
            body = (
                f"Ola, {cliente.nome}! Voce ganhou {code} de cashback no programa de fidelidade."
            )
        else:
            body = notif_msg.format_map(
                defaultdict(
                    str,
                    code=code or "",
                    nome=cliente.nome if cliente else "",
                    value=f"{reward_value:.2f}",
                )
            )
        enqueue_email(
            db,
            tenant_id=campaign.tenant_id,
            customer_id=customer_id,
            subject="Sua recompensa de fidelidade chegou!",
            body=body,
            email_address=cliente.email,
            idempotency_key=f"loyalty:{campaign.id}:{customer_id}:{ref_period}:email",
        )

    return 1


def _revoke_loyalty_reward(
    db: Session,
    *,
    campaign: Campaign,
    execution: CampaignExecution,
) -> int:
    reward_meta = execution.reward_meta or {}
    coupon_id = reward_meta.get("coupon_id")
    cashback_tx_id = reward_meta.get("cashback_tx_id")

    if coupon_id:
        coupon = (
            db.query(Coupon)
            .filter(
                Coupon.id == coupon_id,
                Coupon.tenant_id == campaign.tenant_id,
            )
            .first()
        )
        if coupon is None:
            db.delete(execution)
            return 1

        if coupon.status == CouponStatusEnum.used:
            logger.info(
                "[loyalty_service] Mantendo recompensa %s porque o cupom %s ja foi usado",
                execution.reference_period,
                coupon.code,
            )
            return 0

        if coupon.status == CouponStatusEnum.active:
            coupon.status = CouponStatusEnum.voided

        db.delete(execution)
        return 1

    if cashback_tx_id:
        cashback_tx = (
            db.query(CashbackTransaction)
            .filter(
                CashbackTransaction.id == cashback_tx_id,
                CashbackTransaction.tenant_id == campaign.tenant_id,
            )
            .first()
        )

        if cashback_tx is not None:
            reversal_exists = (
                db.query(CashbackTransaction.id)
                .filter(
                    CashbackTransaction.tenant_id == campaign.tenant_id,
                    CashbackTransaction.source_type == CashbackSourceTypeEnum.reversal,
                    CashbackTransaction.source_id == cashback_tx.id,
                )
                .first()
            )
            if not reversal_exists:
                db.add(
                    CashbackTransaction(
                        tenant_id=campaign.tenant_id,
                        customer_id=execution.customer_id,
                        amount=-(cashback_tx.amount or 0),
                        source_type=CashbackSourceTypeEnum.reversal,
                        source_id=cashback_tx.id,
                        description=(
                            f"Estorno recompensa de fidelidade {campaign.name} "
                            f"({execution.reference_period})"
                        ),
                        tx_type="debit",
                    )
                )

        db.delete(execution)
        return 1

    db.delete(execution)
    return 1


def _append_note(existing: str | None, message: str) -> str:
    base = (existing or "").strip()
    if not base:
        return message
    if message in base:
        return base
    return f"{base} | {message}"


def _is_loyalty_ref(reference_period: str | None) -> bool:
    if not reference_period:
        return False
    return reference_period.startswith("cycle-") or reference_period.startswith("mid-")


def _is_reward_configured(reward_tp: str | None, reward_val: Any) -> bool:
    if reward_tp == "brinde":
        return True
    return Decimal(str(reward_val or 0)) > 0


def _sort_loyalty_refs(refs) -> list[str]:
    def key(ref: str) -> tuple[int, int]:
        if ref.startswith("mid-"):
            return (0, int(ref.split("-", 1)[1]))
        return (1, int(ref.split("-", 1)[1]))

    return sorted(refs, key=key)
