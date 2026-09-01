from types import SimpleNamespace

from app.campaigns.notification_sender import _push_data_for_notification, _send_email


def test_push_data_for_notification_includes_navigation_payload():
    notif = SimpleNamespace(
        idempotency_key="vet-agendamento:42:24h:2026-07-10T15:30:00",
        source="appointment_reminder",
        kind="veterinario_agendamento",
        payload={
            "module": "veterinario",
            "agendamento_id": 42,
            "appointment_id": 42,
        },
    )

    assert _push_data_for_notification(notif) == {
        "idempotency_key": "vet-agendamento:42:24h:2026-07-10T15:30:00",
        "source": "appointment_reminder",
        "kind": "veterinario_agendamento",
        "module": "veterinario",
        "agendamento_id": 42,
        "appointment_id": 42,
    }


def test_push_data_for_campaign_notification_includes_campaign_payload():
    notif = SimpleNamespace(
        idempotency_key="bday:10:55:2026-07-10:push",
        source="campaign",
        kind="birthday_customer",
        payload={
            "target": "coupons",
            "campaign_id": 10,
            "campaign_type": "birthday_customer",
            "coupon_code": "ANIV-123",
        },
    )

    assert _push_data_for_notification(notif) == {
        "idempotency_key": "bday:10:55:2026-07-10:push",
        "source": "campaign",
        "kind": "birthday_customer",
        "target": "coupons",
        "campaign_id": 10,
        "campaign_type": "birthday_customer",
        "coupon_code": "ANIV-123",
    }


def test_campaign_email_uses_central_email_service(monkeypatch):
    sent = {}

    def fake_send_email(**kwargs):
        sent.update(kwargs)
        return True

    monkeypatch.setattr(
        "app.campaigns.notification_sender.email_service.send_email",
        fake_send_email,
    )

    _send_email(
        "cliente@example.com",
        "Feliz aniversário!",
        "Olá!\nTemos um presente para você.",
        "birthday_customer",
    )

    assert sent["to"] == "cliente@example.com"
    assert sent["subject"] == "Feliz aniversário!"
    assert sent["text_body"] == "Olá!\nTemos um presente para você."
    assert "Esta mensagem foi enviada automaticamente" not in sent["html_body"]
    assert sent["simulate_if_unconfigured"] is False


def test_campaign_email_raises_when_central_service_fails(monkeypatch):
    monkeypatch.setattr(
        "app.campaigns.notification_sender.email_service.send_email",
        lambda **kwargs: False,
    )

    try:
        _send_email("cliente@example.com", "Assunto", "Mensagem")
    except RuntimeError as exc:
        assert "serviço central" in str(exc)
    else:
        raise AssertionError("Falha do serviço central deveria gerar nova tentativa")
