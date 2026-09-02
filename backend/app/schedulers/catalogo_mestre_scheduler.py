"""Agendamento do enriquecimento continuo do catalogo mestre."""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db import SessionLocal
from app.services.catalogo_mestre_enrichment_worker import (
    CatalogEnrichmentConfig,
    CatalogMasterEnrichmentWorker,
)


logger = logging.getLogger(__name__)


def _interval_seconds() -> int:
    try:
        value = int(os.getenv("CATALOGO_MESTRE_WORKER_INTERVAL_SECONDS", "60"))
    except ValueError:
        value = 60
    return max(15, min(value, 3600))


class CatalogMasterScheduler:
    def __init__(self) -> None:
        self.config = CatalogEnrichmentConfig.from_env()
        self.scheduler = BackgroundScheduler()
        self.worker = CatalogMasterEnrichmentWorker(
            session_factory=SessionLocal,
            config=self.config,
        )
        if self.config.enabled:
            self.scheduler.add_job(
                func=self.process_batch,
                trigger=IntervalTrigger(seconds=_interval_seconds()),
                id="catalogo_mestre_enrichment",
                name="Catalogo Mestre Enrichment",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )

    def process_batch(self) -> None:
        try:
            stats = self.worker.run_batch()
            if stats.claimed or stats.reason not in {None, "fila_elegivel_vazia"}:
                logger.info("[CATALOGO MESTRE] Lote: %s", stats.to_dict())
        except Exception:
            logger.exception("[CATALOGO MESTRE] Falha inesperada no lote")

    def start(self) -> None:
        self.scheduler.start()
        logger.info(
            "[CATALOGO MESTRE] Scheduler iniciado (enabled=%s, apply=%s)",
            self.config.enabled,
            self.config.apply_enabled,
        )

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
