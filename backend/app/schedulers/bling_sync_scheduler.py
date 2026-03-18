"""Scheduler de sincronização e reconciliação do Bling."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.services.bling_sync_service import BlingSyncService

logger = logging.getLogger(__name__)


class BlingSyncScheduler:
    """Executa retries e auditorias periódicas da integração com o Bling."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._configure_jobs()

    def _configure_jobs(self) -> None:
        self.scheduler.add_job(
            func=self.processar_fila,
            trigger=IntervalTrigger(minutes=1),
            id="bling_sync_queue",
            name="Bling Sync Queue",
            replace_existing=True,
        )
        self.scheduler.add_job(
            func=self.reconciliar_recentes,
            trigger=IntervalTrigger(minutes=15),
            id="bling_sync_recent_reconcile",
            name="Bling Reconcile Recent",
            replace_existing=True,
        )
        self.scheduler.add_job(
            func=self.reconciliar_geral,
            trigger=CronTrigger(hour=2, minute=0),
            id="bling_sync_full_reconcile",
            name="Bling Full Reconcile",
            replace_existing=True,
        )

        logger.info("[BLING SYNC] Jobs configurados:")
        logger.info("   - Fila pendente: a cada 1 minuto")
        logger.info("   - Reconciliação recente: a cada 15 minutos")
        logger.info("   - Auditoria geral: diariamente às 02:00")

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[BLING SYNC] Scheduler iniciado")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("[BLING SYNC] Scheduler parado")

    def processar_fila(self) -> None:
        result = BlingSyncService.process_pending_queue(limit=30)
        if result.get("processados"):
            logger.info("[BLING SYNC] Fila processada: %s", result)

    def reconciliar_recentes(self) -> None:
        result = BlingSyncService.reconcile_recent_products(minutes=30, limit=150)
        if result.get("avaliados"):
            logger.info("[BLING SYNC] Reconciliação recente: %s", result)

    def reconciliar_geral(self) -> None:
        result = BlingSyncService.reconcile_all_products()
        logger.info("[BLING SYNC] Auditoria geral: %s", result)