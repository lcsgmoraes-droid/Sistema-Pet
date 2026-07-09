from datetime import datetime, timedelta

from app.services.appointment_reminders import (
    AppointmentReminderConfig,
    build_reminder_jobs,
)


def test_build_reminder_jobs_uses_day_before_and_custom_hours():
    starts_at = datetime(2026, 7, 10, 15, 30)
    now = starts_at - timedelta(days=2)
    config = AppointmentReminderConfig(
        enabled=True,
        day_before_enabled=True,
        hours_before_enabled=True,
        hours_before=2,
    )

    jobs = build_reminder_jobs(
        config=config,
        tenant_id="tenant-1",
        customer_id=55,
        appointment_id=99,
        starts_at=starts_at,
        module="banho_tosa",
        kind="banho_tosa_agendamento",
        pet_id=12,
        pet_name="Mel",
        title="Lembrete de Banho & Tosa",
        body_for_hours=lambda hours: f"Mel tem banho em {hours}h.",
        now=now,
    )

    assert [job.hours_before for job in jobs] == [24, 2]
    assert [job.scheduled_at for job in jobs] == [
        starts_at - timedelta(hours=24),
        starts_at - timedelta(hours=2),
    ]
    assert jobs[0].payload == {
        "source": "appointment_reminder",
        "kind": "banho_tosa_agendamento",
        "module": "banho_tosa",
        "agendamento_id": 99,
        "appointment_id": 99,
        "pet_id": 12,
        "pet_nome": "Mel",
        "starts_at": "2026-07-10T15:30:00",
        "hours_before": 24,
    }


def test_build_reminder_jobs_skips_disabled_duplicate_and_past_offsets():
    starts_at = datetime(2026, 7, 10, 15, 30)
    config = AppointmentReminderConfig(
        enabled=True,
        day_before_enabled=True,
        hours_before_enabled=True,
        hours_before=24,
    )

    jobs = build_reminder_jobs(
        config=config,
        tenant_id="tenant-1",
        customer_id=55,
        appointment_id=99,
        starts_at=starts_at,
        module="veterinario",
        kind="veterinario_agendamento",
        pet_id=None,
        pet_name=None,
        title="Lembrete de consulta",
        body_for_hours=lambda hours: f"Consulta em {hours}h.",
        now=starts_at - timedelta(hours=25),
    )

    assert [job.hours_before for job in jobs] == [24]

    jobs = build_reminder_jobs(
        config=config,
        tenant_id="tenant-1",
        customer_id=55,
        appointment_id=99,
        starts_at=starts_at,
        module="veterinario",
        kind="veterinario_agendamento",
        pet_id=None,
        pet_name=None,
        title="Lembrete de consulta",
        body_for_hours=lambda hours: f"Consulta em {hours}h.",
        now=starts_at - timedelta(hours=1),
    )

    assert jobs == []

    disabled = AppointmentReminderConfig(
        enabled=False,
        day_before_enabled=True,
        hours_before_enabled=True,
        hours_before=1,
    )
    assert (
        build_reminder_jobs(
            config=disabled,
            tenant_id="tenant-1",
            customer_id=55,
            appointment_id=99,
            starts_at=starts_at,
            module="veterinario",
            kind="veterinario_agendamento",
            pet_id=None,
            pet_name=None,
            title="Lembrete de consulta",
            body_for_hours=lambda hours: f"Consulta em {hours}h.",
            now=starts_at - timedelta(days=2),
        )
        == []
    )
