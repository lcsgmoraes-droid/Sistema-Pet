from types import SimpleNamespace

from app.campaigns.notification_sender import _push_data_for_notification


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
