"""
Handler: Cartao Fidelidade (Carimbos)
====================================

Disparo: purchase_completed
Campanha: loyalty_stamp

Regra:
- usa a venda atual como fonte da verdade
- so contabiliza carimbos se a venda ainda estiver finalizada
- sincroniza a quantidade de carimbos da venda com a regra "1 carimbo a cada X reais"
- sincroniza recompensas emitidas de acordo com o total ativo do cliente
"""

import logging

from sqlalchemy.orm import Session

from app.campaigns.loyalty_service import sync_loyalty_stamps_for_sale
from app.campaigns.models import Campaign, CampaignEventQueue, CampaignTypeEnum

logger = logging.getLogger(__name__)

_SUPPORTED_EVENTS = frozenset({"purchase_completed"})


class LoyaltyHandler:
    """Handler para o cartao fidelidade virtual."""

    def run(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        if event.event_type not in _SUPPORTED_EVENTS:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}
        if campaign.campaign_type != CampaignTypeEnum.loyalty_stamp:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        payload = event.payload or {}
        venda_id = payload.get("venda_id")
        if not venda_id:
            logger.warning(
                "[LoyaltyHandler] Payload incompleto event_id=%d: %s",
                event.id,
                payload,
            )
            return {"evaluated": 0, "rewarded": 0, "errors": 1}

        from app.vendas_models import Venda

        venda = (
            db.query(Venda)
            .filter(Venda.id == int(venda_id), Venda.tenant_id == campaign.tenant_id)
            .first()
        )
        if venda is None or venda.status != "finalizada" or not venda.cliente_id:
            logger.info(
                "[LoyaltyHandler] Ignorando venda=%s porque nao esta finalizada ou nao possui cliente",
                venda_id,
            )
            return {"evaluated": 1, "rewarded": 0, "errors": 0}

        customer_id = int(venda.cliente_id)
        params = campaign.params or {}

        try:
            rewarded = self._process(
                db=db,
                campaign=campaign,
                customer_id=customer_id,
                venda_id=int(venda.id),
                venda_total=float(venda.total or 0),
                params=params,
                source_event_id=event.id,
            )
        except Exception as exc:
            logger.warning("[LoyaltyHandler] Erro customer=%d: %s", customer_id, exc)
            return {"evaluated": 1, "rewarded": 0, "errors": 1}

        return {"evaluated": 1, "rewarded": rewarded, "errors": 0}

    def _process(
        self,
        db,
        campaign,
        customer_id,
        venda_id,
        venda_total,
        params,
        source_event_id,
    ) -> int:
        rank_filter = params.get("rank_filter", "all")
        if rank_filter and rank_filter != "all":
            from app.campaigns.models import CustomerRankHistory

            rank_order = [
                "sem_rank",
                "bronze",
                "silver",
                "gold",
                "diamond",
                "platinum",
            ]
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
                if latest is not None:
                    return 0
            else:
                req_idx = rank_order.index(rank_filter) if rank_filter in rank_order else 0
                cust_idx = rank_order.index(customer_rank) if customer_rank in rank_order else 0
                if cust_idx < req_idx:
                    return 0

        result = sync_loyalty_stamps_for_sale(
            db,
            campaign=campaign,
            customer_id=customer_id,
            venda_id=venda_id,
            venda_total=venda_total,
            source_event_id=source_event_id,
            reason=f"Evento purchase_completed #{source_event_id}",
        )
        return result["awarded"]
