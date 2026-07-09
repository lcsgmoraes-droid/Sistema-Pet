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
