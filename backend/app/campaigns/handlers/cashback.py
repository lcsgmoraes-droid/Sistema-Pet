"""
Handler: Cashback
==================

Disparo:  purchase_completed (evento em tempo real)
Campanha: cashback

Lógica:
  1. Extrai customer_id, valor da venda e canal de compra do payload
  2. Determina o percentual de cashback com base no nível de ranking do cliente
     (consultado em customer_rank_history para o período atual)
  3. Calcula amount = valor_venda * (percentual / 100)
  4. Registra campaign_execution com reference_period = venda_id (idempotência)
  5. Insere cashback_transactions (ledger append-only)
  6. Enfileira notificação de cashback recebido

Parâmetros esperados em campaign.params:
  {
    "bronze_percent": 0,
    "silver_percent": 1.0,
    "gold_percent": 2.0,
    "diamond_percent": 3.0,
    "platinum_percent": 5.0
  }

O saldo disponível é calculado pelos lotes e respectivos vencimentos.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.campaigns.models import (
    Campaign,
    CampaignEventQueue,
    CampaignExecution,
    CampaignTypeEnum,
    CashbackSourceTypeEnum,
    CashbackTransaction,
    CustomerRankHistory,
    RankLevelEnum,
)
from app.campaigns.app_push import enqueue_campaign_push
from app.campaigns.notification_service import enqueue_email
from app.campaigns.channel_scope import normalize_benefit_channel
from app.campaigns.cashback_wallet import get_cashback_wallet, lock_cashback_customer
from app.campaigns.audit import log_campaign_event

logger = logging.getLogger(__name__)

_SUPPORTED_EVENTS = frozenset({"purchase_completed"})

# Mapa: rank_level → chave em params
_RANK_PARAM_KEY = {
    RankLevelEnum.bronze: "bronze_percent",
    RankLevelEnum.silver: "silver_percent",
    RankLevelEnum.gold: "gold_percent",
    RankLevelEnum.diamond: "diamond_percent",
    RankLevelEnum.platinum: "platinum_percent",
}


def _retained_cashback_after_reopening(
    db: Session,
    campaign: Campaign,
    customer_id: int,
    execution: CampaignExecution,
) -> tuple[Decimal, Decimal]:
    """Return the prior award not revoked, including its already expired part.

    Expiration consumes the original entitlement just like redemption. Editing
    a sale must not create a fresh replacement for a benefit that already expired.
    """
    prior_credits = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == campaign.tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.campaign,
            CashbackTransaction.source_id == execution.id,
            CashbackTransaction.amount > 0,
        )
        .all()
    )
    prior_ids = [credit.id for credit in prior_credits]
    refunded_credits = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == campaign.tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.origin_credit_id.in_(prior_ids),
            CashbackTransaction.amount > 0,
        )
        .all()
        if prior_ids
        else []
    )
    wallet = get_cashback_wallet(
        db, tenant_id=campaign.tenant_id, customer_id=customer_id
    )
    retained = sum(
        (Decimal(str(credit.amount)) for credit in prior_credits),
        Decimal("0.00"),
    )
    expired = Decimal("0.00")
    for prior in [*prior_credits, *refunded_credits]:
        revoked = sum(
            (
                -Decimal(str(row[0]))
                for row in db.query(CashbackTransaction.amount)
                .filter(
                    CashbackTransaction.tenant_id == campaign.tenant_id,
                    CashbackTransaction.customer_id == customer_id,
                    CashbackTransaction.source_type == CashbackSourceTypeEnum.reversal,
                    CashbackTransaction.source_id == prior.id,
                    CashbackTransaction.amount < 0,
                )
                .all()
            ),
            Decimal("0.00"),
        )
        retained -= revoked
        expired += wallet.expected_expiration_by_credit.get(prior.id, Decimal("0.00"))
    return max(Decimal("0.00"), retained), expired


def _notify_cashback_award(
    db: Session,
    campaign: Campaign,
    customer_id: int,
    venda_id: int,
    reference_period: str,
    canal: str,
    amount: Decimal,
    rank: RankLevelEnum,
) -> None:
    from app.models import Cliente

    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == customer_id, Cliente.tenant_id == campaign.tenant_id)
        .first()
    )
    if cliente:
        amount_label = f"{amount:.2f}".replace(".", ",")
        push_body = (
            f"Ola, {cliente.nome}! Voce ganhou R$ {amount_label} de cashback "
            "na sua ultima compra. Veja seus beneficios no app."
        )
        enqueue_campaign_push(
            db,
            tenant_id=campaign.tenant_id,
            customer_id=customer_id,
            title="Voce ganhou cashback",
            body=push_body,
            idempotency_key=(
                f"cashback:{campaign.id}:{customer_id}:{reference_period}:push"
            ),
            kind="cashback",
            campaign=campaign,
            payload={
                "target": "benefits",
                "customer_id": customer_id,
                "venda_id": venda_id,
                "cashback_amount": float(amount),
                "rank": rank.value,
                "canal": canal,
                "reward_type": "cashback",
            },
        )
    if cliente and cliente.email:
        amount_label = f"{amount:.2f}".replace(".", ",")
        body = (
            f"Olá, {cliente.nome}! Você ganhou R$ {amount_label} de cashback "
            "na sua última compra. Seu saldo será aplicado na próxima compra."
        )
        enqueue_email(
            db,
            tenant_id=campaign.tenant_id,
            customer_id=customer_id,
            subject="Você ganhou cashback! 💰",
            body=body,
            email_address=cliente.email,
            idempotency_key=(
                f"cashback:{campaign.id}:{customer_id}:{reference_period}:email"
            ),
        )


class CashbackHandler:
    """Handler para cashback baseado em nível de ranking."""

    def run(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        """
        Calcula e credita cashback a cada compra finalizada.

        payload: {"customer_id": N, "venda_id": N, "venda_total": N}
        reference_period = str(venda_id) — garante idempotência por venda.
        Não commita — o commit fica no CampaignEngine.
        """
        if event.event_type not in _SUPPORTED_EVENTS:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}
        if campaign.campaign_type != CampaignTypeEnum.cashback:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        payload = event.payload or {}
        customer_id = payload.get("customer_id")
        venda_id = payload.get("venda_id")
        venda_total = payload.get("venda_total")

        if not customer_id or not venda_id or venda_total is None:
            logger.warning(
                "[CashbackHandler] Payload incompleto event_id=%d: %s",
                event.id,
                payload,
            )
            return {"evaluated": 0, "rewarded": 0, "errors": 1}

        customer_id = int(customer_id)
        venda_id = int(venda_id)
        canal = normalize_benefit_channel(payload.get("canal") or "loja_fisica")

        try:
            rewarded = self._process(
                db=db,
                campaign=campaign,
                customer_id=customer_id,
                venda_id=venda_id,
                source_event_id=event.id,
                canal=canal,
            )
        except Exception as exc:
            logger.warning("[CashbackHandler] Erro customer=%d: %s", customer_id, exc)
            return {"evaluated": 1, "rewarded": 0, "errors": 1}

        return {"evaluated": 1, "rewarded": rewarded, "errors": 0}

    def _process(
        self,
        db,
        campaign,
        customer_id,
        venda_id,
        source_event_id,
        canal="pdv",
    ) -> int:
        from app.vendas_models import Venda

        venda = (
            db.query(Venda)
            .filter(
                Venda.id == venda_id,
                Venda.tenant_id == campaign.tenant_id,
                Venda.cliente_id == customer_id,
            )
            .with_for_update()
            .first()
        )
        if venda is None or venda.status not in {
            "finalizada",
            "baixa_parcial",
            "pago_nf",
            "finalizada_devolucao",
            "finalizada_devolucao_parcial",
        }:
            return 0
        if getattr(venda, "nao_gerar_beneficios", False):
            return 0
        lock_cashback_customer(
            db, tenant_id=campaign.tenant_id, customer_id=customer_id
        )
        from app.campaigns.sale_return_service import remaining_sale_amount

        venda_total = remaining_sale_amount(
            db, tenant_id=campaign.tenant_id, venda=venda
        )
        ref_period = str(venda_id)  # Idempotência por venda

        # Já processou esta venda?
        existing = (
            db.query(CampaignExecution)
            .filter(
                CampaignExecution.tenant_id == campaign.tenant_id,
                CampaignExecution.campaign_id == campaign.id,
                CampaignExecution.customer_id == customer_id,
                CampaignExecution.reference_period == ref_period,
            )
            .first()
        )
        if existing and not (existing.reward_meta or {}).get("cashback_sale_revoked"):
            return 0

        # Descobre o nível do cliente (última entrada histórica)
        rank_row = (
            db.query(CustomerRankHistory)
            .filter(
                CustomerRankHistory.tenant_id == campaign.tenant_id,
                CustomerRankHistory.customer_id == customer_id,
            )
            .order_by(CustomerRankHistory.period.desc())
            .first()
        )
        rank = rank_row.rank_level if rank_row else RankLevelEnum.bronze

        # Percentual de cashback para este nível
        params = campaign.params or {}
        pct_key = _RANK_PARAM_KEY.get(rank, "bronze_percent")
        pct = Decimal(str(params.get(pct_key, 0) or 0))
        # An edited sale keeps the rule that earned its original benefit.
        # Changing campaign settings or rank later must not reprice old sales.
        old_meta = dict(existing.reward_meta or {}) if existing else {}
        if existing and old_meta.get("percent") is not None:
            pct = Decimal(str(old_meta["percent"]))
            rank = RankLevelEnum(old_meta.get("rank") or rank.value)

        entitlement = (
            max(venda_total, Decimal("0.00")) * max(pct, Decimal("0")) / Decimal("100")
        ).quantize(Decimal("0.01"))
        retained = Decimal("0.00")
        amount = entitlement
        if existing:
            # Part of a prior award may already have been redeemed before the
            # sale was reopened. It cannot be clawed back or granted again.
            retained, expired = _retained_cashback_after_reopening(
                db, campaign, customer_id, existing
            )
            consumed = max(retained - expired, Decimal("0.00"))
            retained_excess = max(retained - entitlement, Decimal("0.00"))
            consumed_excess = max(consumed - entitlement, Decimal("0.00"))
            amount = max(Decimal("0.00"), entitlement - retained)
            existing.reward_value = retained + amount
            existing.reward_meta = {
                **old_meta,
                "cashback_sale_revoked": False,
                "percent": float(pct),
                "rank": rank.value,
                "canal": canal,
                "venda_total_base": float(venda_total),
                "cashback_entitlement": float(entitlement),
                "cashback_retained_on_reopening": float(retained),
                "cashback_expired_before_recalculation": float(expired),
                "cashback_consumed_before_recalculation": float(consumed),
                "cashback_retained_excess": float(retained_excess),
                "cashback_consumed_excess": float(consumed_excess),
            }
            existing.source_event_id = source_event_id
            log_campaign_event(
                db=db,
                tenant_id=campaign.tenant_id,
                event="campaign.cashback.sale_recalculated",
                entity_type="campaign_executions",
                entity_id=existing.id,
                metadata={
                    "venda_id": venda_id,
                    "customer_id": customer_id,
                    "previous_sale_total": old_meta.get("venda_total_base"),
                    "sale_total": float(venda_total),
                    "entitlement": float(entitlement),
                    "retained": float(retained),
                    "expired": float(expired),
                    "consumed": float(consumed),
                    "retained_excess": float(retained_excess),
                    "consumed_excess": float(consumed_excess),
                    "credited": float(amount),
                    "source_event_id": source_event_id,
                },
                details=f"Cashback recalculado apos edicao da venda #{venda_id}",
            )
        if amount <= 0:
            return 0

        # Prazo de validade do cashback (em dias, configurável em campaign.params)
        valid_days = int(params.get("cashback_valid_days") or 0)
        expires_at = None
        if valid_days > 0:
            from datetime import datetime, timezone

            expires_at = datetime.now(timezone.utc) + timedelta(days=valid_days)

        # Registra transação de cashback (ledger append-only)
        cashback_tx = CashbackTransaction(
            tenant_id=campaign.tenant_id,
            customer_id=customer_id,
            amount=amount,
            source_type=CashbackSourceTypeEnum.campaign,
            source_id=None,  # será preenchido após flush da execution
            description=f"Cashback {pct}% na venda #{venda_id} (rank {rank.value}, canal {canal})",
            expires_at=expires_at,
            tx_type="credit",
        )
        db.add(cashback_tx)

        # Registra execution
        execution = existing
        if execution is None:
            execution = CampaignExecution(
                tenant_id=campaign.tenant_id,
                campaign_id=campaign.id,
                customer_id=customer_id,
                reference_period=ref_period,
                reward_type="cashback",
                reward_value=amount,
                reward_meta={
                    "percent": float(pct),
                    "rank": rank.value,
                    "venda_id": venda_id,
                    "venda_total_base": float(venda_total),
                    "cashback_entitlement": float(entitlement),
                    "canal": canal,
                },
                source_event_id=source_event_id,
            )
            db.add(execution)
        db.flush()
        cashback_tx.source_id = execution.id

        _notify_cashback_award(
            db, campaign, customer_id, venda_id, ref_period, canal, amount, rank
        )

        logger.info(
            "[CashbackHandler] customer=%d venda=%d rank=%s pct=%s amount=%s",
            customer_id,
            venda_id,
            rank.value,
            pct,
            amount,
        )
        return 1
