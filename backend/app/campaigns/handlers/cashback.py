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

Nota: saldo de cashback = SUM(cashback_transactions.amount) por cliente.
Nunca usar campo de saldo materializado como fonte da verdade.
"""

import logging
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
from app.campaigns.notification_service import enqueue_email

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
                "[CashbackHandler] Payload incompleto event_id=%d: %s", event.id, payload
            )
            return {"evaluated": 0, "rewarded": 0, "errors": 1}

        customer_id = int(customer_id)
        venda_id = int(venda_id)
        venda_total = Decimal(str(venda_total))
        canal = str(payload.get("canal") or "pdv").lower()

        try:
            rewarded = self._process(
                db=db, campaign=campaign,
                customer_id=customer_id, venda_id=venda_id,
                venda_total=venda_total, source_event_id=event.id,
                canal=canal,
            )
        except Exception as exc:
            logger.warning("[CashbackHandler] Erro customer=%d: %s", customer_id, exc)
            return {"evaluated": 1, "rewarded": 0, "errors": 1}

        return {"evaluated": 1, "rewarded": rewarded, "errors": 0}

    def _process(self, db, campaign, customer_id, venda_id, venda_total, source_event_id, canal="pdv") -> int:
        ref_period = str(venda_id)  # Idempotência por venda

        # Já processou esta venda?
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

        # Bônus adicional por canal de compra (PDV / App / Ecommerce)
        _CANAL_BONUS_KEY = {
            "pdv": "pdv_bonus_percent",
            "app": "app_bonus_percent",
            "ecommerce": "ecommerce_bonus_percent",
            "aplicativo": "app_bonus_percent",
        }
        bonus_key = _CANAL_BONUS_KEY.get(canal, "pdv_bonus_percent")
        bonus_pct = Decimal(str(params.get(bonus_key, 0) or 0))
        pct_total = pct + bonus_pct

        if pct_total <= 0:
            return 0  # sem cashback configurado para este nível/canal

        amount = (venda_total * pct_total / Decimal("100")).quantize(Decimal("0.01"))
        if amount <= 0:
            return 0

        canal_label = f"+{bonus_pct}% canal {canal}" if bonus_pct > 0 else f"canal {canal}"

        # Registra transação de cashback (ledger append-only)
        db.add(CashbackTransaction(
            tenant_id=campaign.tenant_id,
            customer_id=customer_id,
            amount=amount,
            source_type=CashbackSourceTypeEnum.campaign,
            source_id=None,  # será preenchido após flush da execution
            description=f"Cashback {pct_total}% na venda #{venda_id} (rank {rank.value}, {canal_label})",
        ))

        # Registra execution
        db.add(CampaignExecution(
            tenant_id=campaign.tenant_id,
            campaign_id=campaign.id,
            customer_id=customer_id,
            reference_period=ref_period,
            reward_type="cashback",
            reward_value=amount,
            reward_meta={"percent": float(pct_total), "rank": rank.value, "venda_id": venda_id, "canal": canal, "bonus_percent": float(bonus_pct)},
            source_event_id=source_event_id,
        ))

        # Notificação
        from app.models import Cliente
        cliente = db.query(Cliente).filter(Cliente.id == customer_id).first()
        if cliente and cliente.email:
            body = (
                f"Olá, {cliente.nome}! Você ganhou R$ {amount:.2f} de cashback "
                f"na sua última compra. Seu saldo será aplicado na próxima compra."
            ).replace(".", ",")
            enqueue_email(
                db,
                tenant_id=campaign.tenant_id, customer_id=customer_id,
                subject="Você ganhou cashback! 💰",
                body=body, email_address=cliente.email,
                idempotency_key=f"cashback:{campaign.id}:{customer_id}:{ref_period}:email",
            )

        logger.info(
            "[CashbackHandler] customer=%d venda=%d rank=%s pct=%s amount=%s",
            customer_id, venda_id, rank.value, pct, amount,
        )
        return 1
