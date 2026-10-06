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
) -> Decimal:
    """Return the prior award that remained with the customer after reopening."""
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
        retained -= wallet.expected_expiration_by_credit.get(prior.id, Decimal("0.00"))
    return max(Decimal("0.00"), retained)


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

    cliente = db.query(Cliente).filter(Cliente.id == customer_id).first()
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
        }:
            return 0
        lock_cashback_customer(
            db, tenant_id=campaign.tenant_id, customer_id=customer_id
        )
        venda_total = Decimal(str(venda.total or 0))
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

        if pct <= 0:
            return 0  # sem cashback configurado para este nível

        amount = (venda_total * pct / Decimal("100")).quantize(Decimal("0.01"))
        if existing:
            # Part of a prior award may already have been redeemed before the
            # sale was reopened. It cannot be clawed back or granted again.
            retained = _retained_cashback_after_reopening(
                db, campaign, customer_id, existing
            )
            amount = max(Decimal("0.00"), amount - retained)
            existing.reward_meta = {
                **(existing.reward_meta or {}),
                "cashback_sale_revoked": False,
            }
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
