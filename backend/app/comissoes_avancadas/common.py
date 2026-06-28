from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class StructuredLogger:
    def info(self, event_type: str, message: str, extra: dict[str, Any] | None = None):
        logger.info(f"[{event_type}] {message}", extra=extra or {})


struct_logger = StructuredLogger()

__all__ = ["StructuredLogger", "logger", "struct_logger"]
