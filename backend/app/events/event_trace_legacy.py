from collections import deque
from datetime import datetime

_TRACE = deque(maxlen=100)


def trace_legacy_event(event_name: str, payload: dict):
    _TRACE.append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_name,
            "payload": payload,
        }
    )


def get_legacy_trace():
    return list(_TRACE)


def clear_legacy_trace():
    _TRACE.clear()
