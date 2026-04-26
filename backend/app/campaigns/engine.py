"""
Campaign Engine — Núcleo de Avaliação e Execução
==================================================

O Campaign Engine separa duas responsabilidades:

1. evaluate(event) → determina se um cliente é elegível para uma campanha
   - Leitura pura (SELECT), sem side effects
   - Retorna lista de (campaign, customer) elegíveis

2. execute(campaign, customer, event) → concede a recompensa
   - Escreve em campaign_executions com ON CONFLICT DO NOTHING
   - Escreve em cashback_transactions, loyalty_stamps, coupons, etc.
   - Enfileira notificação em notification_queue
   - Nunca chama evaluate() — recebe o resultado pronto

Princípios:
- Toda recompensa passa por aqui — nunca direto de endpoint
- Campanhas de origin 'campaign_action' não re-entram como triggers
- Logs de execução (campaign_run_log) sempre criados, nunca atualizados
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.campaigns.models import (
    CAMPAIGN_TRIGGER_EVENTS,
    Campaign,
    CampaignEventQueue,
    CampaignExecution,
    CampaignRunLog,
    CampaignStatusEnum,
    EventOriginEnum,
)
from app.campaigns.channel_scope import (
    campaign_allows_sale_channel,
    is_purchase_benefit_campaign,
    normalize_benefit_channel,
)

logger = logging.getLogger(__name__)


class CampaignEngine:
    """
    Motor principal de campanhas.

    Uso:
        engine = CampaignEngine(db)
        engine.process_event(event)
    """

    def __init__(self, db: Session):
        self.db = db

    def process_event(self, event: CampaignEventQueue) -> None:
        """
        Ponto de entrada do motor.

        1. Valida event_type contra a allowlist
        2. Descarta event_depth > 1 (proteção contra event storm)
        3. Para cada campanha ativa compatível com o event_type:
           a. evaluate() — verifica elegibilidade
           b. execute() — concede recompensa se elegível
        4. Atualiza status do evento na fila
        """
        if event.event_type not in CAMPAIGN_TRIGGER_EVENTS:
            logger.warning(
                "[CampaignEngine] event_type '%s' não está na allowlist — descartado",
                event.event_type,
            )
            event.status = "skipped"
            event.processed_at = datetime.now()
            self.db.commit()
            return

        if event.event_depth > 1:
            logger.warning(
                "[CampaignEngine] event_depth=%d > 1 — descartado (proteção storm)",
                event.event_depth,
            )
            event.status = "skipped"
            event.processed_at = datetime.now()
            self.db.commit()
            return

        try:
            # Buscar campanhas ativas para este tenant
            campaigns = self._get_active_campaigns(
                tenant_id=event.tenant_id,
                event_type=event.event_type,
                sale_channel=(event.payload or {}).get("canal"),
            )

            for campaign in campaigns:
                self._run_campaign(campaign=campaign, event=event)

            event.status = "done"
            event.processed_at = datetime.now()
            self.db.commit()

        except Exception as exc:
            logger.exception("[CampaignEngine] Erro ao processar evento %d: %s", event.id, exc)
            event.retry_count = (event.retry_count or 0) + 1
            event.error_message = str(exc)
            if event.retry_count >= event.max_retries:
                event.status = "failed"
            else:
                event.status = "pending"  # Volta para fila
            self.db.commit()
            raise

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _get_active_campaigns(
        self,
        tenant_id,
        event_type: str,
        sale_channel: Optional[str] = None,
    ) -> list[Campaign]:
        """
        Retorna campanhas ativas ordenadas por prioridade.
        O mapeamento event_type → campaign_type fica nos handlers.
        """
        # TODO: implementar mapeamento event_type → campaign_type
        # Por ora retorna todas as campanhas ativas do tenant
        campaigns = (
            self.db.query(Campaign)
            .filter(
                Campaign.tenant_id == tenant_id,
                Campaign.status == CampaignStatusEnum.active,
            )
            .order_by(Campaign.priority.asc())
            .all()
        )

        if event_type != "purchase_completed":
            return campaigns

        normalized_channel = normalize_benefit_channel(sale_channel)
        filtered: list[Campaign] = []
        for campaign in campaigns:
            if is_purchase_benefit_campaign(campaign) and not campaign_allows_sale_channel(
                campaign,
                normalized_channel,
            ):
                logger.info(
                    "[CampaignEngine] Campanha %s ignorada para canal=%s",
                    campaign.id,
                    normalized_channel,
                )
                continue
            filtered.append(campaign)

        return filtered

    def _run_campaign(self, campaign: Campaign, event: CampaignEventQueue) -> None:
        """
        Executa uma campanha para o evento dado.
        Delega para o handler específico do campaign_type.
        """
        from app.campaigns.handlers import get_handler

        handler = get_handler(campaign.campaign_type)
        if handler is None:
            logger.debug(
                "[CampaignEngine] Sem handler para campaign_type '%s'",
                campaign.campaign_type,
            )
            return

        start = datetime.now()
        evaluated = 0
        rewarded = 0
        errors = 0

        try:
            result = handler.run(db=self.db, campaign=campaign, event=event)
            evaluated = result.get("evaluated", 0)
            rewarded = result.get("rewarded", 0)
            errors = result.get("errors", 0)
        except Exception as exc:
            errors = 1
            logger.exception(
                "[CampaignEngine] Handler erro campaign_id=%d: %s", campaign.id, exc
            )
            raise
        finally:
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)
            run_log = CampaignRunLog(
                tenant_id=campaign.tenant_id,
                campaign_id=campaign.id,
                event_type=event.event_type,
                evaluated=evaluated,
                rewarded=rewarded,
                errors=errors,
                duration_ms=duration_ms,
            )
            self.db.add(run_log)
            # Não commitar aqui — o commit fica no process_event()
