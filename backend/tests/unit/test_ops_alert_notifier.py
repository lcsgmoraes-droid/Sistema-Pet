from app.services import ops_alert_notifier


def _critical_alert() -> dict:
    return {
        "alert_key": "system:watchdog:degraded",
        "scope": "system",
        "kind": "watchdog_degraded",
        "severity": "critical",
        "title": "Watchdog degradado",
        "detail": "Banco lento",
        "action": "Checar pool",
        "latest_event_at": "2026-05-16T21:50:00Z",
        "occurrence_count": 1,
        "payload": {"secret": "nao deve sair"},
    }


def test_notify_ops_alerts_disabled_without_webhook(monkeypatch, tmp_path):
    monkeypatch.delenv("OPS_ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("OPS_ALERT_EMAIL_TO", raising=False)
    monkeypatch.setenv("OPS_ALERT_NOTIFICATION_LOG_PATH", str(tmp_path / "notifications.jsonl"))

    result = ops_alert_notifier.notify_ops_alerts([_critical_alert()])

    assert result["enabled"] is False
    assert result["sent"] == 0
    assert not (tmp_path / "notifications.jsonl").exists()


def test_notify_ops_alerts_sends_email_when_webhook_is_absent(monkeypatch, tmp_path):
    sent_emails = []

    def fake_send_email(*, to, subject, html_body, text_body, simulate_if_unconfigured):
        sent_emails.append(
            {
                "to": to,
                "subject": subject,
                "html_body": html_body,
                "text_body": text_body,
                "simulate_if_unconfigured": simulate_if_unconfigured,
            }
        )
        return True

    log_path = tmp_path / "notifications.jsonl"
    monkeypatch.delenv("OPS_ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("OPS_ALERT_EMAIL_TO", "ops@example.test")
    monkeypatch.setenv("OPS_ALERT_NOTIFICATION_LOG_PATH", str(log_path))
    monkeypatch.setattr(ops_alert_notifier.email_service, "send_email", fake_send_email)

    result = ops_alert_notifier.notify_ops_alerts([_critical_alert()])

    assert result["enabled"] is True
    assert result["status"] == "sent"
    assert result["attempted"] == 1
    assert result["sent"] == 1
    assert result["sent_email"] == 1
    assert result["sent_webhook"] == 0
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "ops@example.test"
    assert sent_emails[0]["subject"] == "[Sistema Pet Ops] critical - Watchdog degradado"
    assert sent_emails[0]["simulate_if_unconfigured"] is False
    assert "system:watchdog:degraded" in sent_emails[0]["text_body"]
    assert "payload" not in sent_emails[0]["text_body"]
    assert "nao deve sair" not in sent_emails[0]["text_body"]
    assert log_path.exists()


def test_notify_ops_alerts_sends_critical_once_and_redacts_result(monkeypatch, tmp_path):
    calls = []

    class _Response:
        def raise_for_status(self):
            return None

    def fake_post(url, *, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _Response()

    log_path = tmp_path / "notifications.jsonl"
    monkeypatch.setenv("OPS_ALERT_WEBHOOK_URL", "https://hooks.example.test/secret-token")
    monkeypatch.setenv("OPS_ALERT_NOTIFICATION_LOG_PATH", str(log_path))
    monkeypatch.setattr(ops_alert_notifier.httpx, "post", fake_post)

    first = ops_alert_notifier.notify_ops_alerts(
        [
            _critical_alert(),
            {"alert_key": "route:slow", "severity": "warning", "title": "Rota lenta"},
        ]
    )
    second = ops_alert_notifier.notify_ops_alerts([_critical_alert()])

    assert first["enabled"] is True
    assert first["attempted"] == 1
    assert first["sent"] == 1
    assert first["sent_webhook"] == 1
    assert "secret-token" not in str(first)
    assert second["attempted"] == 0
    assert second["skipped_duplicate"] == 1
    assert len(calls) == 1
    assert calls[0]["url"].endswith("/secret-token")
    assert calls[0]["json"]["source"] == "sistema_pet.ops_alerts"
    assert calls[0]["json"]["alerts"][0]["alert_key"] == "system:watchdog:degraded"
    assert "payload" not in calls[0]["json"]["alerts"][0]
    assert log_path.exists()
