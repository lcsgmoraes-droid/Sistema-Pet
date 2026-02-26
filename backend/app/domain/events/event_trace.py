import datetime
import threading

_EVENT_TRACE = []
_TRACE_LOCK = threading.Lock()
_MAX_EVENTS = 200


def trace_event(source, event_name, payload=None):
    if payload is None:
        serialized_payload = None
    elif isinstance(payload, dict):
        serialized_payload = payload
    elif hasattr(payload, "__dict__"):
        serialized_payload = {
            k: v
            for k, v in vars(payload).items()
        }
    else:
        serialized_payload = str(payload)[:300]

    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "source": source,
        "event": event_name,
        "payload": serialized_payload,
    }

    with _TRACE_LOCK:
        _EVENT_TRACE.append(entry)

        if len(_EVENT_TRACE) > _MAX_EVENTS:
            _EVENT_TRACE.pop(0)


def get_event_trace():
    with _TRACE_LOCK:
        return list(_EVENT_TRACE)


def clear_event_trace():
    with _TRACE_LOCK:
        _EVENT_TRACE.clear()