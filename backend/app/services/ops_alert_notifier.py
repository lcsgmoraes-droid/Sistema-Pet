from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from html import escape
import json
import os
import threading
from typing import Any

import httpx

from app.services import email_service


_lock = threading.Lock()

_SEVERITY_ORDER = {
    "ok": 0,
    "info": 1,
    "warning": 2,
    "critical": 3,
}

_PUBLIC_ALERT_FIELDS = (
    "alert_key",
    "id",
    "scope",
    "kind",
    "severity",
    "title",
    "detail",
    "action",
    "tenant_id",
    "tenant_name",
    "path",
    "request_id",
    "latest_event_at",
    "latest_at",
    "occurrence_count",
    "score",
)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _notification_log_path() -> str:
    return os.getenv(
        "OPS_ALERT_NOTIFICATION_LOG_PATH",
        os.path.join(os.getcwd(), "logs", "ops_alert_notifications.jsonl"),
    )


def _min_severity() -> str:
    raw = (
        os.getenv("OPS_ALERT_MIN_SEVERITY")
        or os.getenv("OPS_ALERT_WEBHOOK_MIN_SEVERITY")
        or "critical"
    ).strip().lower()
    return raw if raw in _SEVERITY_ORDER else "critical"


def _email_recipients() -> list[str]:
    raw = os.getenv("OPS_ALERT_EMAIL_TO", "").strip()
    if not raw:
        return []
    normalized = raw.replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _severity_allows(alert: dict[str, Any], min_severity: str) -> bool:
    severity = str(alert.get("severity") or "info").lower()
    return _SEVERITY_ORDER.get(severity, 0) >= _SEVERITY_ORDER[min_severity]


def _notification_key(alert: dict[str, Any]) -> str:
    alert_key = str(alert.get("alert_key") or alert.get("id") or alert.get("kind") or "ops_alert")
    latest = str(alert.get("latest_event_at") or alert.get("latest_at") or alert.get("last_seen_at") or "")
    severity = str(alert.get("severity") or "info")
    return f"{alert_key}:{severity}:{latest}"


def _public_alert(alert: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key in _PUBLIC_ALERT_FIELDS:
        if key in alert and alert.get(key) is not None:
            data[key] = alert.get(key)
    if "alert_key" not in data and "id" in data:
        data["alert_key"] = data["id"]
    return data


def _email_subject(alerts: list[dict[str, Any]]) -> str:
    first = alerts[0] if alerts else {}
    severity = str(first.get("severity") or "critical").lower()
    title = str(first.get("title") or first.get("alert_key") or "Alerta Ops")
    return f"[CorePet Ops] {severity} - {title}"[:180]


def _email_body(alerts: list[dict[str, Any]], min_severity: str) -> tuple[str, str]:
    lines = [
        "CorePet Ops - alerta operacional",
        "",
        f"Severidade minima: {min_severity}",
        f"Gerado em: {_utcnow_iso()}",
        "",
    ]
    html_items = []
    for alert in alerts:
        key = str(alert.get("alert_key") or alert.get("id") or alert.get("kind") or "ops_alert")
        severity = str(alert.get("severity") or "info")
        title = str(alert.get("title") or key)
        detail = str(alert.get("detail") or "")
        action = str(alert.get("action") or "")
        request_id = str(alert.get("request_id") or "")
        path = str(alert.get("path") or "")

        lines.extend(
            [
                f"- {severity.upper()} | {title}",
                f"  Chave: {key}",
            ]
        )
        if detail:
            lines.append(f"  Detalhe: {detail}")
        if action:
            lines.append(f"  Acao recomendada: {action}")
        if path:
            lines.append(f"  Rota: {path}")
        if request_id:
            lines.append(f"  Request ID: {request_id}")
        lines.append("")

        html_items.append(
            "<li>"
            f"<strong>{escape(severity.upper())}</strong> - {escape(title)}"
            f"<br><span>Chave: {escape(key)}</span>"
            + (f"<br><span>Detalhe: {escape(detail)}</span>" if detail else "")
            + (f"<br><span>Acao recomendada: {escape(action)}</span>" if action else "")
            + (f"<br><span>Rota: {escape(path)}</span>" if path else "")
            + (f"<br><span>Request ID: {escape(request_id)}</span>" if request_id else "")
            + "</li>"
        )

    text_body = "\n".join(lines).strip()
    html_body = (
        "<html><body>"
        "<h2>CorePet Ops - alerta operacional</h2>"
        f"<p><strong>Severidade minima:</strong> {escape(min_severity)}</p>"
        f"<p><strong>Gerado em:</strong> {escape(_utcnow_iso())}</p>"
        "<ul>"
        + "".join(html_items)
        + "</ul>"
        "</body></html>"
    )
    return html_body, text_body


def _read_sent_keys(max_lines: int = 5000) -> set[str]:
    path = _notification_log_path()
    if not os.path.exists(path):
        return set()

    lines: deque[str] = deque(maxlen=max(1, max_lines))
    try:
        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    lines.append(line)
    except OSError:
        return set()

    keys: set[str] = set()
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("notification_key") and item.get("status") == "sent":
            keys.add(str(item["notification_key"]))
    return keys


def _append_sent_log(notification_keys: list[str]) -> None:
    path = _notification_log_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    created_at = _utcnow_iso()
    with _lock:
        with open(path, "a", encoding="utf-8") as file:
            for key in notification_keys:
                file.write(
                    json.dumps(
                        {
                            "created_at": created_at,
                            "event_type": "ops_alert_notification",
                            "notification_key": key,
                            "status": "sent",
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )


def notify_ops_alerts(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    webhook_url = os.getenv("OPS_ALERT_WEBHOOK_URL", "").strip()
    email_recipients = _email_recipients()
    has_email = bool(email_recipients)
    has_webhook = bool(webhook_url)
    result = {
        "enabled": bool(has_webhook or has_email),
        "status": "disabled" if not (has_webhook or has_email) else "ready",
        "attempted": 0,
        "sent": 0,
        "sent_webhook": 0,
        "sent_email": 0,
        "failed": 0,
        "failed_webhook": 0,
        "failed_email": 0,
        "skipped_duplicate": 0,
        "min_severity": _min_severity(),
    }
    if not (has_webhook or has_email):
        return result

    min_severity = result["min_severity"]
    sent_keys = _read_sent_keys()
    pending: list[tuple[str, dict[str, Any]]] = []
    for alert in alerts:
        if not _severity_allows(alert, str(min_severity)):
            continue
        notification_key = _notification_key(alert)
        if notification_key in sent_keys:
            result["skipped_duplicate"] += 1
            continue
        pending.append((notification_key, _public_alert(alert)))

    if not pending:
        result["status"] = "no_eligible_alerts"
        return result

    payload = {
        "source": "corepet.ops_alerts",
        "created_at": _utcnow_iso(),
        "min_severity": min_severity,
        "alerts": [item for _, item in pending],
    }
    public_alerts = [item for _, item in pending]
    result["attempted"] = len(pending)
    any_sent = False

    if webhook_url:
        try:
            response = httpx.post(
                webhook_url,
                json=payload,
                timeout=_env_float("OPS_ALERT_WEBHOOK_TIMEOUT_SECONDS", 5.0),
            )
            response.raise_for_status()
        except Exception as exc:
            result["failed_webhook"] = len(pending)
            result["error_type"] = type(exc).__name__
        else:
            result["sent_webhook"] = len(pending)
            any_sent = True

    if email_recipients:
        html_body, text_body = _email_body(public_alerts, str(min_severity))
        email_sent = 0
        for recipient in email_recipients:
            if email_service.send_email(
                to=recipient,
                subject=_email_subject(public_alerts),
                html_body=html_body,
                text_body=text_body,
                simulate_if_unconfigured=False,
            ):
                email_sent += 1
        if email_sent:
            result["sent_email"] = len(pending)
            any_sent = True
        if email_sent < len(email_recipients):
            result["failed_email"] = len(pending)

    if not any_sent:
        result["status"] = "failed"
        result["failed"] = len(pending)
        return result

    _append_sent_log([key for key, _ in pending])
    result["status"] = "sent" if result["failed_webhook"] == 0 and result["failed_email"] == 0 else "partial"
    result["sent"] = len(pending)
    result["failed"] = len(pending) if result["status"] == "partial" else 0
    return result
