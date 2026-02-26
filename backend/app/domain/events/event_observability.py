from datetime import datetime

_EVENT_FLOW = []
_STAGE_COUNTERS = {}
PERF_ALERT_THRESHOLD_MS = 80

def log_event(stage: str, event: str, source: str):
    now = datetime.utcnow()

    try:
        _STAGE_COUNTERS[stage] = _STAGE_COUNTERS.get(stage, 0) + 1
    except Exception:
        pass

    duration_ms = None
    if _EVENT_FLOW:
        last = _EVENT_FLOW[-1]
        last_time = datetime.fromisoformat(last["timestamp"])
        duration_ms = (now - last_time).total_seconds() * 1000

    try:
        if duration_ms is not None and duration_ms > PERF_ALERT_THRESHOLD_MS:
            print(f"[PERF_ALERT] {stage} demorou {duration_ms:.2f} ms")
    except Exception:
        pass

    _EVENT_FLOW.append({
        "timestamp": now.isoformat(),
        "stage": stage,
        "event": event,
        "source": source,
        "duration_ms": duration_ms
    })

    if len(_EVENT_FLOW) > 200:
        _EVENT_FLOW.pop(0)

def get_flow():
    return list(_EVENT_FLOW)


def get_stage_counters():
    try:
        return dict(_STAGE_COUNTERS)
    except Exception:
        return {}

def clear_flow():
    _EVENT_FLOW.clear()
