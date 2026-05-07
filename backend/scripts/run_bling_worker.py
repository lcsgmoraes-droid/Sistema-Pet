"""Processo dedicado para jobs de integracao Bling."""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.schedulers.bling_sync_scheduler import BlingSyncScheduler
from app.utils.logger import configure_logging


logger = logging.getLogger("bling_worker")
HEARTBEAT_PATH = Path(os.getenv("BLING_WORKER_HEARTBEAT_PATH", "/tmp/bling_worker_heartbeat"))
_should_stop = False


def _handle_signal(signum: int, _frame) -> None:
    global _should_stop
    _should_stop = True
    logger.info("[BLING WORKER] Sinal recebido: %s", signum)


def _touch_heartbeat() -> None:
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(str(time.time()), encoding="utf-8")


def main() -> None:
    configure_logging()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    scheduler = BlingSyncScheduler()
    scheduler.start()
    logger.info("[BLING WORKER] Worker dedicado iniciado")

    try:
        while not _should_stop:
            _touch_heartbeat()
            time.sleep(15)
    finally:
        scheduler.shutdown()
        logger.info("[BLING WORKER] Worker dedicado finalizado")


if __name__ == "__main__":
    main()
