from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.campaigns.coupon_service import create_coupon
from app.campaigns.models import (
    Campaign,
    CampaignExecution,
    CashbackSourceTypeEnum,
    CashbackTransaction,
    Coupon,
    CouponStatusEnum,
)
from app.campaigns.app_push import enqueue_campaign_push
from app.campaigns.notification_service import enqueue_email
from app.models import Cliente

logger = logging.getLogger(__name__)


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
                "stamps_to_complete_snapshot": reward_meta[
                    "stamps_to_complete_snapshot"
                ],
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

    if cliente:
        if reward_tp == "credit":
            body = f"Ola, {cliente.nome}! Voce ganhou {code} de cashback no programa de fidelidade."
        else:
            body = notif_msg.format_map(
                defaultdict(
                    str,
                    code=code or "",
                    nome=cliente.nome if cliente else "",
                    value=f"{reward_value:.2f}",
                )
            )
        enqueue_campaign_push(
            db,
            tenant_id=campaign.tenant_id,
            customer_id=customer_id,
            title="Sua recompensa chegou",
            body=body,
            idempotency_key=f"loyalty:{campaign.id}:{customer_id}:{ref_period}:push",
            kind="loyalty_reward",
            campaign=campaign,
            payload={
                "target": "coupons" if reward_meta.get("coupon_code") else "benefits",
                "customer_id": customer_id,
                "coupon_code": reward_meta.get("coupon_code"),
                "coupon_id": reward_meta.get("coupon_id"),
                "cashback_tx_id": reward_meta.get("cashback_tx_id"),
                "reward_type": reward_type,
                "reference_period": ref_period,
            },
        )
    if cliente and cliente.email:
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
            revoked_at = datetime.now(timezone.utc)
            reward_meta = dict(execution.reward_meta or {})
            reward_meta["revoked_after_use"] = True
            reward_meta["revoked_reason"] = reason or "cupom_revertido"
            reward_meta["revoked_at"] = revoked_at.isoformat()
            reward_meta["original_consumed_stamps"] = reward_meta.get(
                "original_consumed_stamps",
                reward_meta.get("consumed_stamps"),
            )
            reward_meta["consumed_stamps"] = 0
            execution.reward_meta = reward_meta
            coupon.status = CouponStatusEnum.voided
            coupon.meta = {
                **(coupon.meta or {}),
                "voided_reason": reason or "cupom_revertido",
                "voided_at": revoked_at.isoformat(),
            }
            return 1

        if (
            coupon.status
            in (
                CouponStatusEnum.active,
                CouponStatusEnum.used,
                CouponStatusEnum.expired,
            )
            or force
        ):
            coupon.status = CouponStatusEnum.voided
            coupon.meta = {
                **(coupon.meta or {}),
                "voided_reason": reason,
                "voided_at": datetime.now(timezone.utc).isoformat(),
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
        return max(
            int(
                reward_meta.get("stamps_to_complete_snapshot")
                or default_stamps_to_complete
                or 0
            ),
            0,
        )

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
    return str(execution.reference_period or "").startswith(
        "cycle-"
    ) and not _is_execution_suppressed(execution)


def _sort_loyalty_ref_key(ref: str) -> tuple[int, int]:
    if ref.startswith("mid-"):
        return (0, _extract_loyalty_ref_index(ref))
    return (1, _extract_loyalty_ref_index(ref))
