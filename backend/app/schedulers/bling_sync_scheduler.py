"""Scheduler de sincronizacao e reconciliacao do Bling."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.db import SessionLocal
from app.services.bling_flow_monitor_service import executar_auditoria_background
from app.services.bling_sync_service import BlingSyncService
from app.services.nfe_authorized_reconciliation_service import (
    executar_reconciliacao_automatica_nfes_autorizadas,
)
from app.services.nfe_pending_reconciliation_service import (
    executar_reconciliacao_automatica_nfes_pendentes,
)

logger = logging.getLogger(__name__)


class BlingSyncScheduler:
    """Executa retries e auditorias periodicas da integracao com o Bling."""

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
            func=self.reconciliar_nfes_pendentes,
            trigger=IntervalTrigger(minutes=15),
            id="bling_nfe_pending_reconcile",
            name="Bling NF Pending Reconcile",
            replace_existing=True,
        )
        self.scheduler.add_job(
            func=self.reconciliar_nfes_autorizadas,
            trigger=IntervalTrigger(minutes=15),
            id="bling_nfe_authorized_reconcile",
            name="Bling NF Authorized Reconcile",
            replace_existing=True,
        )
        self.scheduler.add_job(
            func=self.auditar_fluxo_bling,
            trigger=IntervalTrigger(minutes=15),
            id="bling_flow_audit_autofix",
            name="Bling Flow Audit Autofix",
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
        logger.info("   - Reconciliacao recente: a cada 15 minutos")
        logger.info("   - NFs pendentes recentes: a cada 15 minutos")
        logger.info("   - NFs autorizadas sem baixa: a cada 15 minutos")
        logger.info("   - Fluxo pedido/NF/estoque: a cada 15 minutos")
        logger.info("   - Auditoria geral: diariamente as 02:00")

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
            logger.info("[BLING SYNC] Reconciliacao recente: %s", result)

    def reconciliar_nfes_pendentes(self) -> None:
        db = SessionLocal()
        try:
            result = executar_reconciliacao_automatica_nfes_pendentes(
                db,
                dias=3,
                limite_notas_por_tenant=200,
            )
            if result.get("tenants_com_pendencias"):
                logger.info("[BLING SYNC] Reconciliacao automatica de NFs pendentes: %s", result)
        finally:
            db.close()

    def reconciliar_nfes_autorizadas(self) -> None:
        db = SessionLocal()
        try:
            result = executar_reconciliacao_automatica_nfes_autorizadas(
                db,
                dias=5,
                limite_notas_por_tenant=300,
            )
            if result.get("notas_reconciliadas_total"):
                logger.info("[BLING SYNC] Reconciliacao automatica de NFs autorizadas: %s", result)
        finally:
            db.close()

    def auditar_fluxo_bling(self) -> None:
        result = executar_auditoria_background(dias=3, limite=300, auto_fix=True)
        if (
            result.get("incidentes_detectados")
            or result.get("auto_fix_tentados")
            or result.get("auto_fix_sucessos")
        ):
            logger.info("[BLING SYNC] Auditoria automatica do fluxo Bling: %s", result)

    def reconciliar_geral(self) -> None:
        result = BlingSyncService.run_nightly_forced_link_and_sync(link_limit=800, sync_limit=1200)
        logger.info("[BLING SYNC] Rotina 02:00 (vinculo+sync forcado): %s", result)
