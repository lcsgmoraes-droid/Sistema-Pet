"""
Campaign Scheduler — Jobs Agendados (APScheduler)
==================================================

Registra os jobs periódicos do motor de campanhas no APScheduler
já existente no projeto (acerto_scheduler.py usa o mesmo padrão).

Regra: O scheduler NUNCA contém lógica de campanha.
Ele apenas publica um evento na campaign_event_queue e retorna.
Toda a lógica fica nos handlers.

Jobs registrados:
  - daily_birthday_check    → todo dia às 08:00
  - weekly_inactivity_check → toda segunda-feira às 09:00
  - monthly_ranking_recalc  → dia 1 de cada mês às 06:00
  - campaign_worker_tick    → a cada 10 segundos (processa a fila)

Para registrar no main.py:
    from app.campaigns.scheduler import CampaignScheduler
    campaign_scheduler = CampaignScheduler()
    campaign_scheduler.start()
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.campaigns.scheduler_jobs import (
    publish_scheduled_event_for_all_tenants,
    run_auto_execute_drawings,
    run_auto_seed_all_tenants,
    run_auto_send_monthly_highlights,
    run_cashback_expiration_check,
)
from app.campaigns.scheduler_seed import seed_campaigns_for_tenant
from app.campaigns.worker import CampaignWorker
from app.db import SessionLocal

logger = logging.getLogger(__name__)


class CampaignScheduler:
    """
    Gerencia os jobs agendados de campanhas.

    Integra com o APScheduler já existente no projeto.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1}
        )
        self._register_jobs()

    def _register_jobs(self) -> None:
        # Job 1: Verificação diária de aniversários (08:00)
        self.scheduler.add_job(
            func=self._publish_daily_birthday_check,
            trigger=CronTrigger(hour=8, minute=0),
            id="campaign_daily_birthday_check",
            name="Campanhas: Verificação de Aniversários",
            replace_existing=True,
        )

        # Job 2: Verificação semanal de inatividade (segunda às 09:00)
        self.scheduler.add_job(
            func=self._publish_weekly_inactivity_check,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="campaign_weekly_inactivity_check",
            name="Campanhas: Clientes Inativos",
            replace_existing=True,
        )

        # Job 3: Recálculo mensal de ranking (dia 1 às 06:00)
        self.scheduler.add_job(
            func=self._publish_monthly_ranking_recalc,
            trigger=CronTrigger(day=1, hour=6, minute=0),
            id="campaign_monthly_ranking_recalc",
            name="Campanhas: Recálculo de Ranking",
            replace_existing=True,
        )

        # Job 4: Worker da fila (a cada 10 segundos)
        self.scheduler.add_job(
            func=self._tick_worker,
            trigger=IntervalTrigger(seconds=10),
            id="campaign_worker_tick",
            name="Campanhas: Processar Fila",
            replace_existing=True,
        )

        # Job 5: Envio de notificações (a cada 5 minutos)
        self.scheduler.add_job(
            func=self._tick_notifications,
            trigger=IntervalTrigger(minutes=5),
            id="campaign_notification_tick",
            name="Campanhas: Enviar Notificações",
            replace_existing=True,
        )

        # Job 6: Execução automática de sorteios (diário às 10:00)
        self.scheduler.add_job(
            func=self._auto_execute_drawings,
            trigger=CronTrigger(hour=10, minute=0),
            id="campaign_auto_drawings",
            name="Campanhas: Executar Sorteios Automáticos",
            replace_existing=True,
        )

        # Job 7: Destaque Mensal automático (dia 1 às 08:00)
        self.scheduler.add_job(
            func=self._auto_enviar_destaque_mensal,
            trigger=CronTrigger(day=1, hour=8, minute=0),
            id="campaign_destaque_mensal",
            name="Campanhas: Destaque Mensal Automático",
            replace_existing=True,
        )

        # Job 8: Expiração de cashback + alertas (diário às 07:00)
        self.scheduler.add_job(
            func=self._cashback_expiration_check,
            trigger=CronTrigger(hour=7, minute=0),
            id="campaign_cashback_expiration",
            name="Campanhas: Expirar Cashback + Alertas",
            replace_existing=True,
        )

        logger.info("[CampaignScheduler] Jobs registrados:")
        logger.info("   - daily_birthday_check: 08:00")
        logger.info("   - weekly_inactivity_check: toda segunda às 09:00")
        logger.info("   - monthly_ranking_recalc: dia 1 às 06:00")
        logger.info("   - campaign_worker_tick: a cada 10s")
        logger.info("   - campaign_notification_tick: a cada 5 min")
        logger.info("   - auto_drawings: 10:00 diário")
        logger.info("   - destaque_mensal: dia 1 às 08:00")
        logger.info("   - cashback_expiration: 07:00 diário")

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[CampaignScheduler] Iniciado.")
            # Garantir que todos os tenants têm campanhas padrão
            self._auto_seed_all_tenants()

    def shutdown(self, wait: bool = True) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("[CampaignScheduler] Encerrado.")

    # ------------------------------------------------------------------
    # Publicadores de eventos (1 método por job)
    # Apenas publicam o evento na fila — sem lógica de campanha.
    # ------------------------------------------------------------------

    def _publish_daily_birthday_check(self) -> None:
        self._publish_event_for_all_tenants("daily_birthday_check")

    def _publish_weekly_inactivity_check(self) -> None:
        self._publish_event_for_all_tenants("weekly_inactivity_check")

    def _publish_monthly_ranking_recalc(self) -> None:
        self._publish_event_for_all_tenants("monthly_ranking_recalc")

    def _tick_worker(self) -> None:
        """Processa eventos pendentes na fila."""
        try:
            worker = CampaignWorker(db_factory=SessionLocal)
            count = worker.process_batch()
            if count > 0:
                logger.info("[CampaignScheduler] Worker processou %d evento(s)", count)
        except Exception as exc:
            logger.exception("[CampaignScheduler] Erro no worker tick: %s", exc)

    def _tick_notifications(self) -> None:
        """Despacha notificações pendentes (e-mail, push)."""
        try:
            from app.campaigns.notification_sender import NotificationSender

            sender = NotificationSender(db_factory=SessionLocal)
            stats = sender.process_batch()
            if stats["processed"] > 0:
                logger.info("[CampaignScheduler] Notificações: %s", stats)
        except Exception as exc:
            logger.exception("[CampaignScheduler] Erro no notification tick: %s", exc)

    def _auto_execute_drawings(self) -> None:
        run_auto_execute_drawings(db_factory=SessionLocal, logger=logger)

    def _auto_enviar_destaque_mensal(self) -> None:
        run_auto_send_monthly_highlights(db_factory=SessionLocal, logger=logger)

    def _auto_seed_all_tenants(self) -> None:
        run_auto_seed_all_tenants(db_factory=SessionLocal, logger=logger)

    def _publish_event_for_all_tenants(self, event_type: str) -> None:
        publish_scheduled_event_for_all_tenants(
            event_type, db_factory=SessionLocal, logger=logger
        )

    def _cashback_expiration_check(self) -> None:
        run_cashback_expiration_check(db_factory=SessionLocal, logger=logger)


__all__ = ["CampaignScheduler", "seed_campaigns_for_tenant"]
