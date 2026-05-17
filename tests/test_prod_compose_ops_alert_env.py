from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"


def test_backend_prod_compose_exposes_ops_alert_webhook_env():
    compose_text = COMPOSE_PROD.read_text(encoding="utf-8")

    expected_env = [
        "OPS_ALERT_WEBHOOK_URL: ${OPS_ALERT_WEBHOOK_URL:-}",
        "OPS_ALERT_WEBHOOK_MIN_SEVERITY: ${OPS_ALERT_WEBHOOK_MIN_SEVERITY:-critical}",
        "OPS_ALERT_WEBHOOK_TIMEOUT_SECONDS: ${OPS_ALERT_WEBHOOK_TIMEOUT_SECONDS:-5}",
        "OPS_ALERT_NOTIFICATION_LOG_PATH: ${OPS_ALERT_NOTIFICATION_LOG_PATH:-logs/ops_alert_notifications.jsonl}",
    ]

    for item in expected_env:
        assert item in compose_text
