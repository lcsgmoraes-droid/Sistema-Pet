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
    return int(total_stamps or 0) - calculate_loyalty_consumed_stamps(
        completed_cycles,
        stamps_to_complete,
    )


def calculate_loyalty_signed_balance_components(
    total_stamps: int,
    committed_stamps: int,
) -> dict[str, int]:
    raw_total = max(int(total_stamps or 0), 0)
    committed_total = max(int(committed_stamps or 0), 0)
    available_stamps = raw_total - committed_total
    visible_committed = min(raw_total, committed_total)
    debt_stamps = max(committed_total - raw_total, 0)

    return {
        "raw_stamps": raw_total,
        "committed_stamps": committed_total,
        "available_stamps": available_stamps,
        "visible_committed_stamps": visible_committed,
        "debt_stamps": debt_stamps,
    }


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
    executions = _load_loyalty_executions(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        customer_id=customer_id,
    )
    return sum(1 for execution in executions if _is_effective_cycle_execution(execution))


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
    executions = _load_loyalty_executions(
        db,
        tenant_id=campaign.tenant_id,
        campaign_id=campaign.id,
        customer_id=customer_id,
    )
    cycle_executions = [
        execution
        for execution in executions
        if _is_effective_cycle_execution(execution)
    ]
    consumed_total = sum(
        _resolve_consumed_stamps(
            execution,
            default_stamps_to_complete=stamps_to_complete,
        )
        for execution in cycle_executions
    )
    components = calculate_loyalty_signed_balance_components(
        total_stamps,
        consumed_total,
    )

    return {
        "total_stamps": total_stamps,
        "completed_cycles": len(cycle_executions),
        "consumed_stamps": consumed_total,
        "committed_stamps": components["committed_stamps"],
        "converted_stamps": components["visible_committed_stamps"],
        "available_stamps": components["available_stamps"],
        "debt_stamps": components["debt_stamps"],
    }


def summarize_loyalty_balances_for_customer(
    db: Session,
    *,
    tenant_id,
    customer_id: int,
) -> dict[str, int]:
    stamp_campaign_ids = {
        int(campaign_id)
        for (campaign_id,) in (
            db.query(LoyaltyStamp.campaign_id)
            .filter(
                LoyaltyStamp.tenant_id == tenant_id,
                LoyaltyStamp.customer_id == customer_id,
                LoyaltyStamp.voided_at.is_(None),
            )
            .distinct()
            .all()
        )
    }
    execution_campaign_ids = {
        int(campaign_id)
        for (campaign_id,) in (
            db.query(CampaignExecution.campaign_id)
            .filter(
                CampaignExecution.tenant_id == tenant_id,
                CampaignExecution.customer_id == customer_id,
                CampaignExecution.reference_period.like("cycle-%"),
            )
            .distinct()
            .all()
        )
    }
    campaign_ids = sorted(stamp_campaign_ids | execution_campaign_ids)
    if not campaign_ids:
        return {
            "total_carimbos": 0,
            "total_carimbos_brutos": 0,
            "carimbos_comprometidos_total": 0,
            "carimbos_em_debito": 0,
            "carimbos_convertidos": 0,
            "ciclos_concluidos": 0,
        }

    campaigns = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.id.in_(campaign_ids),
        )
        .all()
    )

    total_raw = 0
    total_available = 0
    total_committed = 0
    total_converted = 0
    total_debt = 0
    total_cycles = 0

    for campaign in campaigns:
        balance = get_loyalty_balance_for_campaign(
            db,
            campaign=campaign,
            customer_id=customer_id,
        )
        total_raw += balance["total_stamps"]
        total_available += balance["available_stamps"]
        total_committed += balance["committed_stamps"]
        total_converted += balance["converted_stamps"]
        total_debt += balance["debt_stamps"]
        total_cycles += balance["completed_cycles"]

    return {
        "total_carimbos": total_available,
        "total_carimbos_brutos": total_raw,
        "carimbos_comprometidos_total": total_committed,
        "carimbos_em_debito": total_debt,
        "carimbos_convertidos": total_converted,
        "ciclos_concluidos": total_cycles,
    }


def build_consumed_loyalty_stamp_ids(
    stamps: list[LoyaltyStamp],
    *,
    consumed_count: int,
) -> set[int]:
    active_stamps = sorted(
        [stamp for stamp in stamps if stamp.voided_at is None],
        key=lambda stamp: (stamp.created_at, stamp.id),
    )
    visible_count = min(len(active_stamps), max(int(consumed_count or 0), 0))
    return {int(stamp.id) for stamp in active_stamps[:visible_count]}


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
        "debt_stamps": reward_sync["debt_stamps"],
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
    raw_total_stamps = count_active_loyalty_stamps(
        db,
        tenant_id=campaign.tenant_id,
        campaign_id=campaign.id,
        customer_id=customer_id,
    )
    executions = _load_loyalty_executions(
        db,
        tenant_id=campaign.tenant_id,
        campaign_id=campaign.id,
        customer_id=customer_id,
    )

    cycle_executions = [
        execution
        for execution in executions
        if _is_effective_cycle_execution(execution)
    ]
    suppressed_cycle_executions = [
        execution
        for execution in executions
        if str(execution.reference_period or "").startswith("cycle-")
        and _is_execution_suppressed(execution)
    ]
    mid_executions = {
        execution.reference_period: execution
        for execution in executions
        if str(execution.reference_period or "").startswith("mid-")
    }

    awarded = 0
    revoked = 0

    cycle_reward_enabled = _is_reward_configured(
        params.get("reward_type", "coupon"),
        params.get("reward_value", 0),
    )
    funded_cycles = (
        raw_total_stamps // stamps_to_complete
        if stamps_to_complete > 0 and cycle_reward_enabled
        else 0
    )

    locked_cycles: list[CampaignExecution] = []
    removable_cycles: list[CampaignExecution] = []
    max_cycle_index = 0
    current_cycle_count = len(cycle_executions)
    suppressed_cycle_count = len(suppressed_cycle_executions)

    for execution in [*cycle_executions, *suppressed_cycle_executions]:
        max_cycle_index = max(
            max_cycle_index,
            _extract_loyalty_ref_index(execution.reference_period),
        )
    for execution in cycle_executions:
        if _loyalty_execution_is_locked(db, campaign=campaign, execution=execution):
            locked_cycles.append(execution)
        else:
            removable_cycles.append(execution)

    target_cycle_count = max(
        max(funded_cycles - suppressed_cycle_count, 0),
        len(locked_cycles),
    )
    removable_cycles.sort(
        key=lambda execution: _extract_loyalty_ref_index(execution.reference_period),
        reverse=True,
    )
    while current_cycle_count > target_cycle_count and removable_cycles:
        execution = removable_cycles.pop(0)
        revoked += _revoke_loyalty_reward(
            db,
            campaign=campaign,
            execution=execution,
        )
        current_cycle_count -= 1

    while current_cycle_count < target_cycle_count:
        max_cycle_index += 1
        ref_period = f"cycle-{max_cycle_index}"
        awarded += _give_loyalty_reward(
            db,
            campaign=campaign,
            customer_id=customer_id,
            ref_period=ref_period,
            reward_tp=params.get("reward_type", "coupon"),
            reward_val=params.get("reward_value", 0),
            source_event_id=source_event_id,
            prefix="FIEL",
            notif_msg=params.get(
                "notification_message",
                "Parabens! Seu cartao de fidelidade completou um ciclo. Recompensa: {code}",
            ),
            consumed_stamps=stamps_to_complete,
            stamps_to_complete_snapshot=stamps_to_complete,
        )
        current_cycle_count += 1

    desired_mid_refs = {
        ref
        for ref in build_loyalty_reward_refs(
            total_stamps=raw_total_stamps,
            stamps_to_complete=stamps_to_complete,
            intermediate_stamp=intermediate_stamp,
        )
        if ref.startswith("mid-")
    }

    if intermediate_stamp > 0 and _is_reward_configured(
        params.get("intermediate_reward_type", "coupon"),
        params.get("intermediate_reward_value", 0),
    ):
        for ref_period in sorted(desired_mid_refs, key=_sort_loyalty_ref_key):
            if ref_period in mid_executions:
                continue
            awarded += _give_loyalty_reward(
                db,
                campaign=campaign,
                customer_id=customer_id,
                ref_period=ref_period,
                reward_tp=params.get("intermediate_reward_type", "coupon"),
                reward_val=params.get("intermediate_reward_value", 0),
                source_event_id=source_event_id,
                prefix="FIELMID",
                notif_msg=params.get(
                    "notification_message_intermediate",
                    "Voce atingiu um marco da fidelidade. Recompensa: {code}",
                ),
                consumed_stamps=0,
                stamps_to_complete_snapshot=stamps_to_complete,
            )

    for ref_period, execution in mid_executions.items():
        if ref_period in desired_mid_refs:
            continue
        revoked += _revoke_loyalty_reward(
            db,
            campaign=campaign,
            execution=execution,
        )

    balance = get_loyalty_balance_for_campaign(
        db,
        campaign=campaign,
        customer_id=customer_id,
    )
    return {
        "total_stamps": balance["total_stamps"],
        "available_stamps": balance["available_stamps"],
        "converted_stamps": balance["converted_stamps"],
        "debt_stamps": balance["debt_stamps"],
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


def revoke_loyalty_reward_by_coupon(
    db: Session,
    *,
    tenant_id,
    coupon_id: int,
    reason: str | None = None,
) -> dict[str, Any]:
    matching_execution = None
    for execution in (
        db.query(CampaignExecution)
        .filter(CampaignExecution.tenant_id == tenant_id)
        .all()
    ):
        reward_meta = execution.reward_meta or {}
        if int(reward_meta.get("coupon_id") or 0) == int(coupon_id):
            matching_execution = execution
            break

    if matching_execution is None:
        return {"matched": False, "revoked": False}

    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == matching_execution.campaign_id,
            Campaign.tenant_id == tenant_id,
        )
        .first()
    )
    if campaign is None:
        return {"matched": True, "revoked": False}

    revoked = _revoke_loyalty_reward(
        db,
        campaign=campaign,
        execution=matching_execution,
        force=True,
        reason=reason,
    )
    if revoked:
        sync_loyalty_rewards_for_customer(
            db,
            campaign=campaign,
            customer_id=matching_execution.customer_id,
            source_event_id=None,
        )

    return {"matched": True, "revoked": bool(revoked)}


def backfill_loyalty_reward_consumption_meta(
    db: Session,
    *,
    tenant_id=None,
) -> dict[str, int]:
    query = db.query(CampaignExecution).filter(
        CampaignExecution.reference_period.like("cycle-%"),
    )
    if tenant_id is not None:
        query = query.filter(CampaignExecution.tenant_id == tenant_id)

    executions = query.order_by(CampaignExecution.id.asc()).all()
    updated = 0

    for execution in executions:
        reward_meta = dict(execution.reward_meta or {})
        if "consumed_stamps" in reward_meta and "stamps_to_complete_snapshot" in reward_meta:
            continue

        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == execution.campaign_id,
                Campaign.tenant_id == execution.tenant_id,
            )
            .first()
        )
        stamps_to_complete = int(
            ((campaign.params if campaign else {}) or {}).get("stamps_to_complete", 10) or 0
        )
        reward_meta["consumed_stamps"] = max(stamps_to_complete, 0)
        reward_meta["stamps_to_complete_snapshot"] = max(stamps_to_complete, 0)
        execution.reward_meta = reward_meta
        updated += 1

    db.flush()
    return {"updated": updated}


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
    consumed_stamps: int = 0,
    stamps_to_complete_snapshot: int = 0,
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
    reward_meta: dict[str, Any] = {
        "consumed_stamps": max(int(consumed_stamps or 0), 0),
        "stamps_to_complete_snapshot": max(int(stamps_to_complete_snapshot or 0), 0),
    }
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
            meta={
                "reference_period": ref_period,
                "consumed_stamps": reward_meta["consumed_stamps"],
                "stamps_to_complete_snapshot": reward_meta["stamps_to_complete_snapshot"],
            },
        )
        code = coupon.code
        reward_meta.update({"coupon_id": coupon.id, "coupon_code": code})
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
        reward_meta["cashback_tx_id"] = tx.id
        reward_type = "cashback"
        code = f"R$ {reward_value:.2f}"
    elif reward_tp == "brinde":
        reward_meta.update({"tipo": "brinde", "reference_period": ref_period})
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
    force: bool = False,
    reason: str | None = None,
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

        if coupon.status == CouponStatusEnum.used and not force:
            logger.info(
                "[loyalty_service] Mantendo recompensa %s porque o cupom %s ja foi usado",
                execution.reference_period,
                coupon.code,
            )
            return 0

        if force and coupon.status == CouponStatusEnum.used:
            reward_meta = dict(execution.reward_meta or {})
            reward_meta["revoked_after_use"] = True
            reward_meta["revoked_reason"] = reason or "cupom_revertido"
            reward_meta["revoked_at"] = datetime.now(timezone.utc).isoformat()
            reward_meta["original_consumed_stamps"] = reward_meta.get(
                "original_consumed_stamps",
                reward_meta.get("consumed_stamps"),
            )
            reward_meta["consumed_stamps"] = 0
            execution.reward_meta = reward_meta
            coupon.status = CouponStatusEnum.voided
            return 1

        if coupon.status in (CouponStatusEnum.active, CouponStatusEnum.used, CouponStatusEnum.expired) or force:
            coupon.status = CouponStatusEnum.voided
            if reason:
                coupon.meta = {
                    **(coupon.meta or {}),
                    "voided_reason": reason,
                }

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


def _load_loyalty_executions(
    db: Session,
    *,
    tenant_id,
    campaign_id: int,
    customer_id: int,
) -> list[CampaignExecution]:
    return (
        db.query(CampaignExecution)
        .filter(
            CampaignExecution.tenant_id == tenant_id,
            CampaignExecution.campaign_id == campaign_id,
            CampaignExecution.customer_id == customer_id,
        )
        .all()
    )


def _resolve_consumed_stamps(
    execution: CampaignExecution,
    *,
    default_stamps_to_complete: int,
) -> int:
    reward_meta = dict(execution.reward_meta or {})
    if reward_meta.get("revoked_after_use"):
        return 0
    if "consumed_stamps" in reward_meta:
        return max(int(reward_meta.get("consumed_stamps") or 0), 0)

    if str(execution.reference_period or "").startswith("cycle-"):
        return max(int(reward_meta.get("stamps_to_complete_snapshot") or default_stamps_to_complete or 0), 0)

    return 0


def _extract_loyalty_ref_index(reference_period: str | None) -> int:
    if not reference_period or "-" not in reference_period:
        return 0
    try:
        return int(str(reference_period).split("-", 1)[1])
    except (TypeError, ValueError):
        return 0


def _loyalty_execution_is_locked(
    db: Session,
    *,
    campaign: Campaign,
    execution: CampaignExecution,
) -> bool:
    if _is_execution_suppressed(execution):
        return False

    reward_meta = execution.reward_meta or {}
    coupon_id = reward_meta.get("coupon_id")
    if not coupon_id:
        return False

    coupon = (
        db.query(Coupon)
        .filter(
            Coupon.id == coupon_id,
            Coupon.tenant_id == campaign.tenant_id,
        )
        .first()
    )
    return bool(coupon and coupon.status == CouponStatusEnum.used)


def _is_reward_configured(reward_tp: str | None, reward_val: Any) -> bool:
    if reward_tp == "brinde":
        return True
    return Decimal(str(reward_val or 0)) > 0


def _is_execution_suppressed(execution: CampaignExecution) -> bool:
    reward_meta = execution.reward_meta or {}
    return bool(reward_meta.get("revoked_after_use"))


def _is_effective_cycle_execution(execution: CampaignExecution) -> bool:
    return (
        str(execution.reference_period or "").startswith("cycle-")
        and not _is_execution_suppressed(execution)
    )


def _sort_loyalty_ref_key(ref: str) -> tuple[int, int]:
    if ref.startswith("mid-"):
        return (0, _extract_loyalty_ref_index(ref))
    return (1, _extract_loyalty_ref_index(ref))
