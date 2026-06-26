from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.campaigns.audit import log_campaign_event
from app.campaigns.models import (
    Campaign,
    CampaignExecution,
    LoyaltyStamp,
)

from app.campaigns.loyalty_rewards import (
    _append_note,
    _extract_loyalty_ref_index,
    _give_loyalty_reward,
    _is_effective_cycle_execution,
    _is_execution_suppressed,
    _is_reward_configured,
    _load_loyalty_executions,
    _loyalty_execution_is_locked,
    _resolve_consumed_stamps,
    _revoke_loyalty_reward,
    _sort_loyalty_ref_key,
)

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
    return sum(
        1 for execution in executions if _is_effective_cycle_execution(execution)
    )


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
        int(stamp.stamp_index or 1): stamp for stamp in existing_auto_stamps
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
    if (
        added
        or reactivated
        or voided
        or reward_sync["awarded"]
        or reward_sync["revoked"]
    ):
        log_campaign_event(
            db=db,
            tenant_id=campaign.tenant_id,
            event="campaign.loyalty.stamps_synced",
            entity_type="campaign_loyalty_stamps",
            entity_id=venda_id,
            metadata={
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "customer_id": customer_id,
                "venda_id": venda_id,
                "source_event_id": source_event_id,
                "reason": reason,
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
            },
            details=f"Carimbos sincronizados para venda #{venda_id}",
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

    # Placeholders suppressed by a reversed used coupon stay for audit/history,
    # but the business rule remains: every configured full cycle funds one reward.
    target_cycle_count = max(funded_cycles, len(locked_cycles))
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
    # campaign_executions e TenantScoped: query ORM exige tenant no contexto. tenant_id
    # None => itera todos os tenants (enumerados via tabela tenants, global/whitelist)
    # com contexto proprio por iteracao.
    from uuid import UUID as _UUID
    from app.models import Tenant
    from app.tenancy.context import clear_current_tenant, set_current_tenant

    if tenant_id is None:
        updated_total = 0
        for (tid_raw,) in db.query(Tenant.id).all():
            try:
                tid = _UUID(str(tid_raw))
            except (TypeError, ValueError):
                continue
            updated_total += backfill_loyalty_reward_consumption_meta(
                db, tenant_id=tid
            )["updated"]
        return {"updated": updated_total}

    set_current_tenant(
        tenant_id if isinstance(tenant_id, _UUID) else _UUID(str(tenant_id))
    )
    try:
        executions = (
            db.query(CampaignExecution)
            .filter(
                CampaignExecution.reference_period.like("cycle-%"),
                CampaignExecution.tenant_id == tenant_id,
            )
            .order_by(CampaignExecution.id.asc())
            .all()
        )
        updated = 0

        for execution in executions:
            reward_meta = dict(execution.reward_meta or {})
            if (
                "consumed_stamps" in reward_meta
                and "stamps_to_complete_snapshot" in reward_meta
            ):
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
                ((campaign.params if campaign else {}) or {}).get(
                    "stamps_to_complete", 10
                )
                or 0
            )
            reward_meta["consumed_stamps"] = max(stamps_to_complete, 0)
            reward_meta["stamps_to_complete_snapshot"] = max(stamps_to_complete, 0)
            execution.reward_meta = reward_meta
            updated += 1

        db.flush()
        return {"updated": updated}
    finally:
        clear_current_tenant()
