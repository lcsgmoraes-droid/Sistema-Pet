"""Reverte apenas os beneficios causados pelo evento de uma baixa em lote.

O chamador controla commit/rollback e deve manter o lock da venda. O snapshot
anterior acompanha o evento porque carimbos antigos nao possuem source_event_id.
Nenhum resgate de cashback ou desconto aplicado anteriormente e restituido aqui.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from app.audit_log import log_action
from app.campaigns.cashback_wallet import get_cashback_wallet, lock_cashback_customer
from app.campaigns.loyalty_rewards import _resolve_consumed_stamps
from app.campaigns.models import (
    Campaign,
    CampaignEventQueue,
    CampaignExecution,
    CampaignTypeEnum,
    CashbackSourceTypeEnum,
    CashbackTransaction,
    Coupon,
    CouponRedemption,
    CouponStatusEnum,
    LoyaltyStamp,
    NotificationQueue,
    NotificationStatusEnum,
)
from app.vendas_models import Venda

CENT = Decimal("0.01")


def _money(value):
    return Decimal(str(value or 0)).quantize(CENT)


def _conflict(detail):
    raise HTTPException(
        409, f"Nao foi possivel estornar a baixa: {detail}. Nenhum valor foi alterado."
    )


def snapshot_beneficios_baixa_lote(db, tenant_id, venda_id):
    """Captura referencias anteriores sob o lock da venda, sem conceder beneficios."""
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if venda is None:
        raise HTTPException(404, "Venda nao encontrada")
    stamps = (
        db.query(LoyaltyStamp)
        .filter_by(tenant_id=tenant_id, venda_id=venda_id, is_manual=False)
        .filter(LoyaltyStamp.voided_at.is_(None))
        .all()
    )
    if not venda.cliente_id:
        return {
            "cliente_id": None,
            "carimbos_ativos_ids": [],
            "execucoes_ids": [],
            "cupons_ativos_ids": [],
            "notificacoes_ids": [],
        }
    executions = (
        db.query(CampaignExecution.id)
        .filter_by(tenant_id=tenant_id, customer_id=venda.cliente_id)
        .all()
    )
    coupons = (
        db.query(Coupon.id)
        .filter_by(
            tenant_id=tenant_id,
            customer_id=venda.cliente_id,
            status=CouponStatusEnum.active,
        )
        .all()
    )
    notifications = (
        db.query(NotificationQueue.id)
        .filter_by(tenant_id=tenant_id, customer_id=venda.cliente_id)
        .all()
    )
    return {
        "cliente_id": int(venda.cliente_id),
        "carimbos_ativos_ids": [int(stamp.id) for stamp in stamps],
        "execucoes_ids": [int(row[0]) for row in executions],
        "cupons_ativos_ids": [int(row[0]) for row in coupons],
        "notificacoes_ids": [int(row[0]) for row in notifications],
    }


def _cashback_plan(*, roots, credits, adjustments, wallet):
    """Distingue consumo efetivo de expiracao, estorno anterior e resgate devolvido."""
    granted = sum((_money(row.amount) for row in roots), Decimal("0.00"))
    reversed_amount = sum((-_money(row.amount) for row in adjustments), Decimal("0.00"))
    expired = sum(
        (
            wallet.expected_expiration_by_credit.get(row.id, Decimal("0.00"))
            for row in credits
        ),
        Decimal("0.00"),
    )
    available = sum(
        (wallet.remaining_by_credit.get(row.id, Decimal("0.00")) for row in credits),
        Decimal("0.00"),
    )
    consumed = _money(granted - reversed_amount - expired - available)
    if consumed > 0:
        _conflict(
            "o cashback concedido por esse pagamento ja foi utilizado; reverta primeiro seu uso"
        )
    if consumed < 0:
        _conflict("o historico do cashback nao fecha com o beneficio concedido")
    return [
        (row, _money(wallet.remaining_by_credit.get(row.id, 0)))
        for row in credits
        if wallet.remaining_by_credit.get(row.id, 0) > 0
    ]


def _validar_cupom(db, tenant_id, coupon):
    redemption = (
        db.query(CouponRedemption.id)
        .filter_by(tenant_id=tenant_id, coupon_id=coupon.id)
        .filter(CouponRedemption.voided_at.is_(None))
        .first()
    )
    if coupon.status == CouponStatusEnum.used or redemption:
        _conflict(
            f"o cupom {coupon.code} gerado por esse pagamento ja foi utilizado; reverta primeiro seu uso"
        )


def _validar_recompensas_posteriores(db, tenant_id, customer_id, stamps, executions):
    """Nao cria debito em fidelidade nem revoga recompensas de outra compra."""
    target_ids = {row.id for row in executions}
    for campaign_id in {row.campaign_id for row in stamps}:
        campaign = (
            db.query(Campaign).filter_by(tenant_id=tenant_id, id=campaign_id).first()
        )
        if campaign is None:
            _conflict("a campanha dos carimbos nao esta disponivel para conferencia")
        active = (
            db.query(LoyaltyStamp)
            .filter_by(
                tenant_id=tenant_id, campaign_id=campaign_id, customer_id=customer_id
            )
            .filter(LoyaltyStamp.voided_at.is_(None))
            .all()
        )
        after = len(active) - sum(row.campaign_id == campaign_id for row in stamps)
        others = (
            db.query(CampaignExecution)
            .filter_by(
                tenant_id=tenant_id, campaign_id=campaign_id, customer_id=customer_id
            )
            .all()
        )
        others = [
            row
            for row in others
            if row.id not in target_ids
            and not (row.reward_meta or {}).get("revoked_after_use")
        ]
        committed = sum(
            _resolve_consumed_stamps(
                row,
                default_stamps_to_complete=int(
                    (campaign.params or {}).get("stamps_to_complete", 10) or 0
                ),
            )
            for row in others
        )
        if committed > after:
            _conflict(
                "os carimbos desse pagamento sustentam uma recompensa posterior; confira a fidelidade antes de estornar"
            )
        for row in others:
            reference = str(row.reference_period or "")
            if reference.startswith("mid-"):
                threshold = int(
                    (campaign.params or {}).get("intermediate_stamp", 0) or 0
                )
                try:
                    required = int(reference.split("-", 1)[1]) * threshold
                except ValueError:
                    _conflict("o marco historico da fidelidade nao esta comprovado")
                if threshold <= 0 or required > after:
                    _conflict(
                        "os carimbos desse pagamento sustentam uma recompensa intermediaria posterior"
                    )


def estornar_beneficios_baixa_lote(db, tenant_id, venda_id, evento_id, motivo):
    """Valida todos os beneficios antes de compensar; nunca comita.

    Retorna contadores para a auditoria do lote. HTTP 409 exige rollback da
    transacao inteira pelo chamador. evento_id=None significa baixa parcial,
    que nao enfileirou purchase_completed e portanto nao concedeu beneficios.
    """
    result = {
        "evento_id": evento_id,
        "carimbos_estornados": 0,
        "cupons_estornados": 0,
        "cashback_estornado": "0.00",
        "execucoes_estornadas": 0,
        "notificacoes_canceladas": 0,
    }
    if evento_id is None:
        return result
    venda = (
        db.query(Venda)
        .filter_by(tenant_id=tenant_id, id=venda_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if venda is None:
        raise HTTPException(404, "Venda nao encontrada")
    event = (
        db.query(CampaignEventQueue)
        .filter_by(tenant_id=tenant_id, id=evento_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if event is None or str((event.payload or {}).get("venda_id")) != str(venda_id):
        _conflict("o evento de beneficios nao corresponde a essa venda")
    payload = dict(event.payload or {})
    if payload.get("baixa_lote_estornado"):
        return result
    customer_id = venda.cliente_id
    if customer_id and str(payload.get("customer_id")) != str(customer_id):
        _conflict("o cliente do evento difere do cliente da venda")
    if customer_id:
        lock_cashback_customer(db, tenant_id=tenant_id, customer_id=customer_id)
    snapshot = payload.get("baixa_lote_beneficios_anteriores")
    if snapshot is not None and str(snapshot.get("cliente_id")) != str(customer_id):
        _conflict("o cliente do historico dos beneficios difere da venda")
    executions = (
        db.query(CampaignExecution)
        .filter_by(tenant_id=tenant_id, source_event_id=evento_id)
        .populate_existing()
        .with_for_update()
        .all()
    )
    if any(str(row.customer_id) != str(customer_id) for row in executions):
        _conflict("ha recompensas de outro cliente associadas ao evento")
    previous_executions = set((snapshot or {}).get("execucoes_ids", []))
    if any(row.id in previous_executions for row in executions):
        _conflict(
            "uma recompensa anterior foi recalculada por esse evento e exige conferencia"
        )
    stamps = (
        db.query(LoyaltyStamp)
        .filter_by(tenant_id=tenant_id, venda_id=venda_id, is_manual=False)
        .filter(LoyaltyStamp.voided_at.is_(None))
        .populate_existing()
        .with_for_update()
        .all()
    )
    if snapshot is None and (stamps or executions):
        _conflict("o lancamento antigo nao registra o estado anterior dos beneficios")
    previous_stamps = set((snapshot or {}).get("carimbos_ativos_ids", []))
    if previous_stamps - {row.id for row in stamps}:
        _conflict(
            "os carimbos anteriores mudaram depois desse pagamento e exigem conferencia"
        )
    stamps = [row for row in stamps if row.id not in previous_stamps]
    later_events = (
        db.query(CampaignEventQueue)
        .filter_by(tenant_id=tenant_id, event_type="purchase_completed")
        .filter(CampaignEventQueue.id > evento_id)
        .all()
    )
    if any(
        str((row.payload or {}).get("venda_id")) == str(venda_id)
        and row.status in {"done", "processing"}
        for row in later_events
    ):
        _conflict(
            "a venda recebeu outro evento de beneficios depois desse pagamento; confira os lancamentos posteriores"
        )
    _validar_recompensas_posteriores(db, tenant_id, customer_id, stamps, executions)
    coupons = (
        (
            db.query(Coupon)
            .filter_by(tenant_id=tenant_id, customer_id=customer_id)
            .populate_existing()
            .with_for_update()
            .all()
        )
        if customer_id
        else []
    )
    coupon_ids = {
        int((row.reward_meta or {})["coupon_id"])
        for row in executions
        if (row.reward_meta or {}).get("coupon_id")
    }
    for coupon in coupons:
        meta = coupon.meta or {}
        source = meta.get("reactivated_source_event_id") or meta.get("source_event_id")
        if str(source) == str(evento_id) and str(meta.get("source_venda_id")) == str(
            venda_id
        ):
            coupon_ids.add(coupon.id)
    previous_coupons = set((snapshot or {}).get("cupons_ativos_ids", []))
    coupons = [
        row
        for row in coupons
        if row.id in coupon_ids and row.id not in previous_coupons
    ]
    if coupon_ids - {row.id for row in coupons} - previous_coupons:
        _conflict("um cupom vinculado ao evento nao esta disponivel para conferencia")
    for coupon in coupons:
        _validar_cupom(db, tenant_id, coupon)
    plans = []
    execution_campaigns = {}
    wallet = (
        get_cashback_wallet(db, tenant_id=tenant_id, customer_id=customer_id)
        if customer_id
        else None
    )
    for execution in executions:
        campaign = (
            db.query(Campaign)
            .filter_by(tenant_id=tenant_id, id=execution.campaign_id)
            .first()
        )
        if campaign is None:
            _conflict("a campanha da recompensa nao esta disponivel")
        execution_campaigns[execution.id] = campaign
        if execution.reward_type in {"brinde", "free_gift"}:
            _conflict(
                "a recompensa em brinde exige conferencia da entrega antes do estorno"
            )
        if execution.reward_type != "cashback":
            if not (execution.reward_meta or {}).get("coupon_id"):
                _conflict("o tipo da recompensa nao possui estorno automatico")
            continue
        roots = (
            db.query(CashbackTransaction)
            .filter_by(
                tenant_id=tenant_id,
                customer_id=customer_id,
                source_type=CashbackSourceTypeEnum.campaign,
                source_id=execution.id,
            )
            .filter(CashbackTransaction.amount > 0)
            .all()
        )
        descendants = (
            (
                db.query(CashbackTransaction)
                .filter_by(tenant_id=tenant_id, customer_id=customer_id)
                .filter(
                    CashbackTransaction.origin_credit_id.in_([row.id for row in roots]),
                    CashbackTransaction.amount > 0,
                )
                .all()
            )
            if roots
            else []
        )
        credits = [*roots, *descendants]
        if not roots and _money(execution.reward_value) > 0:
            _conflict("a concessao original de cashback nao esta comprovada")
        adjustments = (
            (
                db.query(CashbackTransaction)
                .filter_by(
                    tenant_id=tenant_id,
                    customer_id=customer_id,
                    source_type=CashbackSourceTypeEnum.reversal,
                )
                .filter(
                    CashbackTransaction.source_id.in_([row.id for row in credits]),
                    CashbackTransaction.amount < 0,
                )
                .all()
            )
            if credits
            else []
        )
        plans.extend(
            _cashback_plan(
                roots=roots, credits=credits, adjustments=adjustments, wallet=wallet
            )
        )
    audit_executions = [
        {
            "id": row.id,
            "campaign_id": row.campaign_id,
            "customer_id": row.customer_id,
            "reference_period": row.reference_period,
            "reward_type": row.reward_type,
            "reward_value": str(row.reward_value),
            "reward_meta": dict(row.reward_meta or {}),
        }
        for row in executions
    ]
    # Toda validacao acima e anterior a qualquer alteracao deste helper.
    now = datetime.now(timezone.utc)
    for credit, amount in plans:
        db.add(
            CashbackTransaction(
                tenant_id=tenant_id,
                customer_id=customer_id,
                amount=-amount,
                source_type=CashbackSourceTypeEnum.reversal,
                source_id=credit.id,
                tx_type="debit",
                description=f"Estorno da baixa em lote (evento #{evento_id}), venda #{venda_id}: {motivo}"[
                    :500
                ],
            )
        )
    for stamp in stamps:
        stamp.voided_at = now
        stamp.voided_origin = "automatic"
        stamp.notes = f"{stamp.notes or ''} | Estorno baixa em lote: {motivo}"[-500:]
    for coupon in coupons:
        coupon.status = CouponStatusEnum.voided
        coupon.meta = {
            **(coupon.meta or {}),
            "voided_reason": "baixa_lote_estornada",
            "voided_at": now.isoformat(),
            "baixa_lote_evento_estornado": evento_id,
        }
    for execution in executions:
        campaign = execution_campaigns[execution.id]
        if campaign.campaign_type == CampaignTypeEnum.cashback:
            execution.reward_meta = {
                **(execution.reward_meta or {}),
                "cashback_sale_revoked": True,
                "cashback_sale_revoked_at": now.isoformat(),
                "baixa_lote_evento_estornado": evento_id,
            }
        else:
            # A auditoria abaixo conserva o snapshot completo. Fidelidade precisa
            # liberar a referencia cycle/mid para poder premiar a baixa corrigida.
            db.delete(execution)
    keys = {
        f"cashback:{row.campaign_id}:{customer_id}:{row.reference_period}:{channel}"
        for row in executions
        if execution_campaigns[row.id].campaign_type == CampaignTypeEnum.cashback
        for channel in ("push", "email")
    }
    keys.update(
        f"loyalty:{row.campaign_id}:{customer_id}:{row.reference_period}:{channel}"
        for row in executions
        if execution_campaigns[row.id].campaign_type == CampaignTypeEnum.loyalty_stamp
        for channel in ("push", "email")
    )
    keys.update(
        f"quick_repurchase:{row.campaign_id}:{customer_id}:{row.id}:push"
        for row in coupons
    )
    notifications = (
        (
            db.query(NotificationQueue)
            .filter_by(tenant_id=tenant_id, customer_id=customer_id)
            .filter(
                NotificationQueue.idempotency_key.in_(keys),
                NotificationQueue.status.in_(
                    [NotificationStatusEnum.pending, NotificationStatusEnum.failed]
                ),
            )
            .with_for_update()
            .all()
        )
        if keys
        else []
    )
    for notification in notifications:
        if notification.id not in set((snapshot or {}).get("notificacoes_ids", [])):
            notification.status = NotificationStatusEnum.skipped
            result["notificacoes_canceladas"] += 1
    event.status = "skipped"
    event.processed_at = now
    event.payload = {
        **payload,
        "baixa_lote_estornado": True,
        "baixa_lote_estornado_em": now.isoformat(),
        "baixa_lote_motivo_estorno": motivo,
    }
    result.update(
        carimbos_estornados=len(stamps),
        cupons_estornados=len(coupons),
        cashback_estornado=str(sum((amount for _, amount in plans), Decimal("0.00"))),
        execucoes_estornadas=len(executions),
    )
    log_action(
        db=db,
        tenant_id=tenant_id,
        user_id=None,
        action="business.campaign.baixa_lote.reversed",
        entity_type="campaign_event_queue",
        entity_id=evento_id,
        old_value={
            "execucoes": audit_executions,
            "carimbos_ids": [row.id for row in stamps],
            "cupons_ids": [row.id for row in coupons],
        },
        new_value=result,
        details=f"Estorno de beneficios da baixa em lote da venda #{venda_id}: {motivo}",
        commit=False,
    )
    db.flush()
    return result


__all__ = ["snapshot_beneficios_baixa_lote", "estornar_beneficios_baixa_lote"]
