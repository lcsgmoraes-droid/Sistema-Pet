"""
Handler: Cartão Fidelidade (Carimbos)
======================================

Disparo:  purchase_completed (evento em tempo real)
Campanha: loyalty_stamp

Lógica:
  1. Extrai customer_id e venda_id do payload do evento
  2. Verifica se o valor da venda ≥ params["min_purchase_value"]
  3. Usa INSERT INTO loyalty_stamps ... ON CONFLICT DO NOTHING (idempotência)
  4. Conta carimbos válidos do cliente para esta campanha
  5. Se atingiu params["stamps_to_complete"]:
     gera recompensa (crédito ou cupom) + registra campaign_execution
     + enfileira notificação de "cartão completo"
  6. Se atingiu params["intermediate_stamp"] (opcional):
     gera recompensa intermediária

Parâmetros esperados em campaign.params:
  {
    "min_purchase_value": 50.00,     # R$ mínimo para ganhar carimbo
    "stamps_to_complete": 10,        # carimbos para completar cartão
    "reward_type": "credit",         # "credit" ou "coupon"
    "reward_value": 50.00,           # valor da recompensa ao completar
    "intermediate_stamp": 5,         # null = sem recompensa intermediária
    "intermediate_reward_type": "coupon",
    "intermediate_reward_value": 10.00
  }
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.campaigns.coupon_service import create_coupon
from app.campaigns.models import (
    Campaign,
    CampaignEventQueue,
    CampaignExecution,
    CampaignTypeEnum,
    LoyaltyStamp,
)
from app.campaigns.notification_service import enqueue_email

logger = logging.getLogger(__name__)

_SUPPORTED_EVENTS = frozenset({"purchase_completed"})


class LoyaltyHandler:
    """Handler para o cartão fidelidade virtual (carimbos)."""

    def run(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        """
        Processa carimbo de fidelidade a cada compra elegível.

        payload esperado: {"customer_id": N, "venda_id": N, "venda_total": N}
        Retorna {"evaluated", "rewarded", "errors"}.
        Não commita — o commit fica no CampaignEngine.
        """
        if event.event_type not in _SUPPORTED_EVENTS:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}
        if campaign.campaign_type != CampaignTypeEnum.loyalty_stamp:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        payload = event.payload or {}
        customer_id = payload.get("customer_id")
        venda_id = payload.get("venda_id")
        venda_total = float(payload.get("venda_total", 0) or 0)

        if not customer_id or not venda_id:
            logger.warning(
                "[LoyaltyHandler] Payload incompleto event_id=%d: %s", event.id, payload
            )
            return {"evaluated": 0, "rewarded": 0, "errors": 1}

        customer_id = int(customer_id)
        venda_id = int(venda_id)
        params = campaign.params or {}

        try:
            rewarded = self._process(
                db=db,
                campaign=campaign,
                customer_id=customer_id,
                venda_id=venda_id,
                venda_total=venda_total,
                params=params,
                source_event_id=event.id,
            )
        except Exception as exc:
            logger.warning("[LoyaltyHandler] Erro customer=%d: %s", customer_id, exc)
            return {"evaluated": 1, "rewarded": 0, "errors": 1}

        return {"evaluated": 1, "rewarded": rewarded, "errors": 0}

    def _process(
        self, db, campaign, customer_id, venda_id, venda_total, params, source_event_id
    ) -> int:
        min_value = float(params.get("min_purchase_value", 0) or 0)
        stamps_to_complete = int(params.get("stamps_to_complete", 10))
        reward_type = params.get("reward_type", "coupon")
        reward_value = float(params.get("reward_value", 0) or 0)
        intermediate_stamp = params.get("intermediate_stamp")  # None = sem recompensa intermediária
        intermediate_type = params.get("intermediate_reward_type", "coupon")
        intermediate_value = float(params.get("intermediate_reward_value", 0) or 0)

        # Compra atinge o valor mínimo?
        if min_value > 0 and venda_total < min_value:
            return 0

        # Filtro por nível de ranking do cliente?
        rank_filter = params.get("rank_filter", "all")
        if rank_filter and rank_filter != "all":
            from app.campaigns.models import CustomerRankHistory
            _RANK_ORDER = ["sem_rank", "bronze", "silver", "gold", "diamond", "platinum"]
            latest = (
                db.query(CustomerRankHistory)
                .filter(
                    CustomerRankHistory.tenant_id == campaign.tenant_id,
                    CustomerRankHistory.customer_id == customer_id,
                )
                .order_by(CustomerRankHistory.period.desc())
                .first()
            )
            customer_rank = latest.rank_level.value if latest else "sem_rank"
            if rank_filter == "sem_rank":
                # Só clientes sem histórico de ranking
                if latest is not None:
                    return 0
            else:
                req_idx = _RANK_ORDER.index(rank_filter) if rank_filter in _RANK_ORDER else 0
                cust_idx = _RANK_ORDER.index(customer_rank) if customer_rank in _RANK_ORDER else 0
                if cust_idx < req_idx:
                    return 0

        # Tenta inserir carimbo (idempotente por UNIQUE tenant+customer+venda)
        stamp = LoyaltyStamp(
            tenant_id=campaign.tenant_id,
            customer_id=customer_id,
            venda_id=venda_id,
            campaign_id=campaign.id,
        )
        try:
            db.add(stamp)
            db.flush()  # Dispara o UNIQUE constraint imediatamente
        except IntegrityError:
            db.rollback()
            logger.debug(
                "[LoyaltyHandler] Carimbo já existe customer=%d venda=%d",
                customer_id, venda_id,
            )
            return 0  # Venda já foi contabilizada antes

        # Conta carimbos válidos deste cliente para esta campanha
        total_stamps = (
            db.query(func.count(LoyaltyStamp.id))
            .filter(
                LoyaltyStamp.tenant_id == campaign.tenant_id,
                LoyaltyStamp.campaign_id == campaign.id,
                LoyaltyStamp.customer_id == customer_id,
                LoyaltyStamp.voided_at.is_(None),
            )
            .scalar()
        ) or 0

        rewarded = 0

        # Recompensa de cartão completo (a cada N carimbos)
        if total_stamps > 0 and total_stamps % stamps_to_complete == 0:
            cycle = total_stamps // stamps_to_complete
            ref_period = f"cycle-{cycle}"
            rewarded += self._give_reward(
                db=db, campaign=campaign, customer_id=customer_id,
                ref_period=ref_period, reward_tp=reward_type, reward_val=reward_value,
                source_event_id=source_event_id, prefix="FIEL",
                notif_msg=params.get(
                    "notification_message",
                    "Parabéns! Seu cartão está completo 🎉 Recompensa: {code}",
                ),
            )

        # Recompensa intermediária (se configurada)
        if (
            intermediate_stamp
            and intermediate_value > 0
            and total_stamps > 0
            and total_stamps % int(intermediate_stamp) == 0
            and total_stamps % stamps_to_complete != 0  # Não duplica com cartão completo
        ):
            mid_cycle = total_stamps // int(intermediate_stamp)
            ref_period = f"mid-{mid_cycle}"
            rewarded += self._give_reward(
                db=db, campaign=campaign, customer_id=customer_id,
                ref_period=ref_period, reward_tp=intermediate_type, reward_val=intermediate_value,
                source_event_id=source_event_id, prefix="FIELMID",
                notif_msg=params.get(
                    "notification_message_intermediate",
                    "Você está na metade! Ganhou: {code}",
                ),
            )

        return rewarded

    def _give_reward(self, db, campaign, customer_id, ref_period, reward_tp,
                     reward_val, source_event_id, prefix, notif_msg) -> int:
        from app.models import Cliente

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

        reward_meta = {}
        code = None
        if reward_tp == "coupon":
            coupon = create_coupon(
                db, tenant_id=campaign.tenant_id, campaign=campaign,
                customer_id=customer_id, coupon_type="fixed",
                discount_value=reward_val, channel="all",
                valid_days=30, prefix=prefix,
                meta={"reference_period": ref_period},
            )
            code = coupon.code
            reward_meta = {"coupon_id": coupon.id, "coupon_code": code}

        db.add(CampaignExecution(
            tenant_id=campaign.tenant_id, campaign_id=campaign.id,
            customer_id=customer_id, reference_period=ref_period,
            reward_type=f"{reward_tp}:fixed", reward_value=reward_val,
            reward_meta=reward_meta, source_event_id=source_event_id,
        ))

        # Notificação por e-mail
        cliente = db.query(Cliente).filter(Cliente.id == customer_id).first()
        if cliente and cliente.email and code:
            body = notif_msg.format(code=code, nome=cliente.nome)
            enqueue_email(
                db, tenant_id=campaign.tenant_id, customer_id=customer_id,
                subject="Sua recompensa de fidelidade chegou! 🎁",
                body=body, email_address=cliente.email,
                idempotency_key=f"loyalty:{campaign.id}:{customer_id}:{ref_period}:email",
            )
        return 1
