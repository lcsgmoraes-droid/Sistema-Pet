"""Scheduler de sincronizacao e reconciliacao do Bling."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging
import os

from app.db import SessionLocal
from app.services.bling_flow_monitor_service import executar_auditoria_background
from app.services.bling_sync_service import BlingSyncService
from app.services.nfe_authorized_reconciliation_service import (
    executar_reconciliacao_automatica_nfes_autorizadas,
)
from app.services.nfe_pending_reconciliation_service import (
    executar_reconciliacao_automatica_nfes_pendentes,
)
from app.services.pedido_duplicate_reconciliation_service import (
    executar_reconciliacao_automatica_duplicidades_pedidos,
)
from app.services.pedido_status_reconciliation_service import (
    executar_reconciliacao_automatica_status_pedidos,
)

logger = logging.getLogger(__name__)

BLING_QUEUE_INTERVAL_SECONDS = int(os.getenv("BLING_QUEUE_INTERVAL_SECONDS", "20"))
BLING_RECENT_RECONCILE_INTERVAL_MINUTES = int(os.getenv("BLING_RECENT_RECONCILE_INTERVAL_MINUTES", "60"))
BLING_RECENT_RECONCILE_LIMIT = int(os.getenv("BLING_RECENT_RECONCILE_LIMIT", "40"))
BLING_NFE_PENDING_RECONCILE_INTERVAL_MINUTES = int(os.getenv("BLING_NFE_PENDING_RECONCILE_INTERVAL_MINUTES", "30"))
BLING_NFE_PENDING_RECONCILE_LIMIT = int(os.getenv("BLING_NFE_PENDING_RECONCILE_LIMIT", "60"))
BLING_NFE_AUTH_RECONCILE_INTERVAL_MINUTES = int(os.getenv("BLING_NFE_AUTH_RECONCILE_INTERVAL_MINUTES", "30"))
BLING_NFE_AUTH_RECONCILE_LIMIT = int(os.getenv("BLING_NFE_AUTH_RECONCILE_LIMIT", "120"))
BLING_ORDER_STATUS_RECONCILE_INTERVAL_MINUTES = int(os.getenv("BLING_ORDER_STATUS_RECONCILE_INTERVAL_MINUTES", "60"))
BLING_ORDER_STATUS_RECONCILE_LIMIT = int(os.getenv("BLING_ORDER_STATUS_RECONCILE_LIMIT", "15"))
BLING_DUPLICATES_RECONCILE_INTERVAL_MINUTES = int(os.getenv("BLING_DUPLICATES_RECONCILE_INTERVAL_MINUTES", "60"))
BLING_DUPLICATES_RECONCILE_LIMIT = int(os.getenv("BLING_DUPLICATES_RECONCILE_LIMIT", "10"))
BLING_FLOW_AUDIT_INTERVAL_MINUTES = int(os.getenv("BLING_FLOW_AUDIT_INTERVAL_MINUTES", "60"))
BLING_FLOW_AUDIT_LIMIT = int(os.getenv("BLING_FLOW_AUDIT_LIMIT", "80"))


class BlingSyncScheduler:
    """Executa retries e auditorias periodicas da integracao com o Bling."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._configure_jobs()

    def _configure_jobs(self) -> None:
        self.scheduler.add_job(
            func=self.processar_fila,
            trigger=IntervalTrigger(seconds=max(BLING_QUEUE_INTERVAL_SECONDS, 5)),
            id="bling_sync_queue",
            name="Bling Sync Queue",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            func=self.reconciliar_recentes,
            trigger=IntervalTrigger(minutes=max(BLING_RECENT_RECONCILE_INTERVAL_MINUTES, 5)),
            id="bling_sync_recent_reconcile",
            name="Bling Reconcile Recent",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            func=self.reconciliar_nfes_pendentes,
            trigger=IntervalTrigger(minutes=max(BLING_NFE_PENDING_RECONCILE_INTERVAL_MINUTES, 5)),
            id="bling_nfe_pending_reconcile",
            name="Bling NF Pending Reconcile",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            func=self.reconciliar_nfes_autorizadas,
            trigger=IntervalTrigger(minutes=max(BLING_NFE_AUTH_RECONCILE_INTERVAL_MINUTES, 5)),
            id="bling_nfe_authorized_reconcile",
            name="Bling NF Authorized Reconcile",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            func=self.reconciliar_status_pedidos,
            trigger=IntervalTrigger(minutes=max(BLING_ORDER_STATUS_RECONCILE_INTERVAL_MINUTES, 5)),
            id="bling_order_status_reconcile",
            name="Bling Order Status Reconcile",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            func=self.reconciliar_duplicidades_pedidos,
            trigger=IntervalTrigger(minutes=max(BLING_DUPLICATES_RECONCILE_INTERVAL_MINUTES, 5)),
            id="bling_order_duplicates_reconcile",
            name="Bling Order Duplicate Reconcile",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            func=self.auditar_fluxo_bling,
            trigger=IntervalTrigger(minutes=max(BLING_FLOW_AUDIT_INTERVAL_MINUTES, 5)),
            id="bling_flow_audit_autofix",
            name="Bling Flow Audit Autofix",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            func=self.reconciliar_geral,
            trigger=CronTrigger(hour=2, minute=0),
            id="bling_sync_full_reconcile",
            name="Bling Full Reconcile",
            replace_existing=True,
        )

        logger.info("[BLING SYNC] Jobs configurados:")
        logger.info("   - Fila pendente: a cada %ss", max(BLING_QUEUE_INTERVAL_SECONDS, 5))
        logger.info("   - Reconciliacao recente: a cada %s min", max(BLING_RECENT_RECONCILE_INTERVAL_MINUTES, 5))
        logger.info("   - NFs pendentes recentes: a cada %s min", max(BLING_NFE_PENDING_RECONCILE_INTERVAL_MINUTES, 5))
        logger.info("   - NFs autorizadas sem baixa: a cada %s min", max(BLING_NFE_AUTH_RECONCILE_INTERVAL_MINUTES, 5))
        logger.info("   - Status de pedidos recentes: a cada %s min", max(BLING_ORDER_STATUS_RECONCILE_INTERVAL_MINUTES, 5))
        logger.info("   - Duplicidades seguras por pedido loja: a cada %s min", max(BLING_DUPLICATES_RECONCILE_INTERVAL_MINUTES, 5))
        logger.info("   - Fluxo pedido/NF/estoque: a cada %s min", max(BLING_FLOW_AUDIT_INTERVAL_MINUTES, 5))
        logger.info("   - Auditoria geral: diariamente as 02:00")

    def _should_defer_secondary_job(self, job_name: str) -> bool:
        snapshot = BlingSyncService.get_secondary_job_guard_snapshot()
        if not snapshot.get("defer_secondary_jobs"):
            return False

        logger.info(
            "[BLING SYNC] %s adiado para priorizar estoque: reason=%s ready=%s total=%s forced=%s cooldown_until=%s",
            job_name,
            snapshot.get("reason"),
            snapshot.get("ready_pending"),
            snapshot.get("total_pending"),
            snapshot.get("forced_pending"),
            snapshot.get("cooldown_until"),
        )
        return True

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[BLING SYNC] Scheduler iniciado")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("[BLING SYNC] Scheduler parado")

    def processar_fila(self) -> None:
        result = BlingSyncService.process_pending_queue(limit=10)
        if result.get("processados"):
            logger.info("[BLING SYNC] Fila processada: %s", result)

    def reconciliar_recentes(self) -> None:
        if self._should_defer_secondary_job("bling_sync_recent_reconcile"):
            return
        result = BlingSyncService.reconcile_recent_products(minutes=30, limit=BLING_RECENT_RECONCILE_LIMIT)
        if result.get("avaliados"):
            logger.info("[BLING SYNC] Reconciliacao recente: %s", result)

    def reconciliar_nfes_pendentes(self) -> None:
        if self._should_defer_secondary_job("bling_nfe_pending_reconcile"):
            return
        db = SessionLocal()
        try:
            result = executar_reconciliacao_automatica_nfes_pendentes(
                db,
                dias=3,
                limite_notas_por_tenant=BLING_NFE_PENDING_RECONCILE_LIMIT,
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
                limite_notas_por_tenant=BLING_NFE_AUTH_RECONCILE_LIMIT,
            )
            if result.get("notas_reconciliadas_total"):
                logger.info("[BLING SYNC] Reconciliacao automatica de NFs autorizadas: %s", result)
        finally:
            db.close()

    def reconciliar_status_pedidos(self) -> None:
        if self._should_defer_secondary_job("bling_order_status_reconcile"):
            return
        db = SessionLocal()
        try:
            result = executar_reconciliacao_automatica_status_pedidos(
                db,
                dias=7,
                limite_pedidos_por_tenant=BLING_ORDER_STATUS_RECONCILE_LIMIT,
            )
            if result.get("confirmados_total") or result.get("cancelados_total") or result.get("erros_total"):
                logger.info("[BLING SYNC] Reconciliacao automatica de status dos pedidos: %s", result)
        finally:
            db.close()

    def reconciliar_duplicidades_pedidos(self) -> None:
        db = SessionLocal()
        try:
            result = executar_reconciliacao_automatica_duplicidades_pedidos(
                db,
                dias=7,
                limite_grupos_por_tenant=BLING_DUPLICATES_RECONCILE_LIMIT,
            )
            if result.get("grupos_consolidados_total") or result.get("erros_total"):
                logger.info("[BLING SYNC] Reconciliacao automatica de duplicidades dos pedidos: %s", result)
        finally:
            db.close()

    def auditar_fluxo_bling(self) -> None:
        if self._should_defer_secondary_job("bling_flow_audit_autofix"):
            return
        result = executar_auditoria_background(dias=3, limite=BLING_FLOW_AUDIT_LIMIT, auto_fix=True)
        if (
            result.get("incidentes_detectados")
            or result.get("auto_fix_tentados")
            or result.get("auto_fix_sucessos")
        ):
            logger.info("[BLING SYNC] Auditoria automatica do fluxo Bling: %s", result)

    def reconciliar_geral(self) -> None:
        if self._should_defer_secondary_job("bling_sync_full_reconcile"):
            return
        result = BlingSyncService.run_nightly_forced_link_and_sync(link_limit=800, sync_limit=1200)
        logger.info("[BLING SYNC] Rotina 02:00 (vinculo+sync forcado): %s", result)
