"""
Campaign Worker — Processador da Fila de Eventos (SKIP LOCKED)
===============================================================

O worker puxa eventos da tabela campaign_event_queue usando
SELECT FOR UPDATE SKIP LOCKED, garantindo que 2 workers não
processem o mesmo evento ao mesmo tempo.

Fase 1: rodado pelo APScheduler (intervalo de 10 segundos).
Fase 2+: substituído por Celery worker sem alterar o CampaignEngine.

Uso:
    worker = CampaignWorker(db_factory=SessionLocal)
    worker.process_batch(batch_size=50)
"""

import logging
from datetime import datetime
from typing import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.campaigns.engine import CampaignEngine
from app.campaigns.models import CampaignEventQueue

logger = logging.getLogger(__name__)

# Máximo de eventos processados por rodada
DEFAULT_BATCH_SIZE = 50


class CampaignWorker:
    """
    Processa eventos da fila campaign_event_queue.

    - Usa SKIP LOCKED para concorrência segura entre workers
    - Cada evento é processado em sua própria transação
    - Falhas individuais não bloqueiam o batch
    """

    def __init__(self, db_factory: Callable[[], Session]):
        self.db_factory = db_factory

    def process_batch(self, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
        """
        Processa até batch_size eventos pendentes.
        Retorna o número de eventos processados.
        """
        processed = 0

        event_ids: list[int] = []
        db = self.db_factory()
        try:
            # Busca e trava eventos pendentes (SKIP LOCKED)
            events = (
                db.query(CampaignEventQueue)
                .filter(CampaignEventQueue.status == "pending")
                .with_for_update(skip_locked=True)
                .order_by(CampaignEventQueue.created_at.asc())
                .limit(batch_size)
                .all()
            )

            if not events:
                return 0

            # Captura IDs e marca como 'processing' antes de fechar sessão
            for event in events:
                event.status = "processing"
                event_ids.append(event.id)
            db.commit()
        finally:
            db.close()

        # Processa cada evento em transação própria (sessão nova por evento)
        for event_id in event_ids:
            self._process_one(event_id=event_id)
            processed += 1

        return processed

    def _process_one(self, event_id: int) -> None:
        """Processa um único evento em transação isolada."""
        db = self.db_factory()
        try:
            event = db.get(CampaignEventQueue, event_id)
            if event is None:
                logger.warning("[Worker] Evento %d não encontrado", event_id)
                return

            engine = CampaignEngine(db=db)
            engine.process_event(event)

        except Exception as exc:
            logger.exception("[Worker] Falha no evento %d: %s", event_id, exc)
            db.rollback()
        finally:
            db.close()
