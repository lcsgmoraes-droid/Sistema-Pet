"""Processo dedicado ao enriquecimento continuo do catalogo mestre."""

from __future__ import annotations

# ruff: noqa: E402

import logging
import os
import signal
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.schedulers.catalogo_mestre_scheduler import CatalogMasterScheduler
from app.utils.logger import configure_logging


logger = logging.getLogger("catalogo_mestre_worker")
DEFAULT_HEARTBEAT_PATH = ROOT_DIR / "data" / "catalogo_mestre_worker_heartbeat"
HEARTBEAT_PATH = Path(
    os.getenv("CATALOGO_MESTRE_WORKER_HEARTBEAT_PATH", str(DEFAULT_HEARTBEAT_PATH))
)
_should_stop = False


def _handle_signal(signum: int, _frame) -> None:
    global _should_stop
    _should_stop = True
    logger.info("[CATALOGO MESTRE] Sinal recebido: %s", signum)


def _touch_heartbeat() -> None:
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(str(time.time()), encoding="utf-8")


def main() -> None:
    configure_logging()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    scheduler = CatalogMasterScheduler()
    scheduler.start()
    logger.info("[CATALOGO MESTRE] Worker dedicado iniciado")
    try:
        while not _should_stop:
            _touch_heartbeat()
            time.sleep(15)
    finally:
        scheduler.shutdown()
        logger.info("[CATALOGO MESTRE] Worker dedicado finalizado")


if __name__ == "__main__":
    main()
