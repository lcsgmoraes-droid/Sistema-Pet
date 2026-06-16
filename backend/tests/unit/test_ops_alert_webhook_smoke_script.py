import os

from app.services import ops_alert_webhook_smoke as script


def test_smoke_script_fails_closed_without_webhook(monkeypatch, capsys):
    monkeypatch.delenv("OPS_ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("OPS_ALERT_EMAIL_TO", raising=False)

    exit_code = script.main([])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "OPS_ALERT_WEBHOOK_URL" in captured.err
    assert "OPS_ALERT_EMAIL_TO" in captured.err


def test_smoke_script_accepts_email_channel_without_webhook(monkeypatch, capsys):
    monkeypatch.delenv("OPS_ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("OPS_ALERT_EMAIL_TO", "ops@example.test")
    calls = []

    def fake_notify(alerts):
        calls.append(alerts)
        return {
            "enabled": True,
            "status": "sent",
            "attempted": 1,
            "sent": 1,
            "sent_email": 1,
            "sent_webhook": 0,
            "failed": 0,
            "skipped_duplicate": 0,
        }

    monkeypatch.setattr(script, "notify_ops_alerts", fake_notify)

    exit_code = script.main(["--label", "email-pytest"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ops@example.test" not in captured.out
    assert calls[0][0]["kind"] == "ops_notifier_test"


def test_smoke_script_does_not_print_secret_webhook(monkeypatch, capsys):
    monkeypatch.setenv(
        "OPS_ALERT_WEBHOOK_URL", "https://hooks.example.test/super-secret-token"
    )
    calls = []

    def fake_notify(alerts):
        calls.append(alerts)
        return {
            "enabled": True,
            "status": "sent",
            "attempted": 1,
            "sent": 1,
            "failed": 0,
            "skipped_duplicate": 0,
        }

    monkeypatch.setattr(script, "notify_ops_alerts", fake_notify)

    exit_code = script.main(["--label", "pytest"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "super-secret-token" not in captured.out
    assert "super-secret-token" not in captured.err
    assert calls[0][0]["kind"] == "ops_notifier_test"
    assert calls[0][0]["severity"] == "critical"
    assert calls[0][0]["title"] == "Teste controlado de alerta Ops"
    assert os.getenv("OPS_ALERT_WEBHOOK_URL") not in str(calls[0])
