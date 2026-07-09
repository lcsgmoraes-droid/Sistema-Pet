from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable


@dataclass(frozen=True)
class AppointmentReminderConfig:
    enabled: bool = True
    day_before_enabled: bool = True
    hours_before_enabled: bool = True
    hours_before: int = 1


@dataclass(frozen=True)
class ReminderJob:
    tenant_id: object
    customer_id: int
    appointment_id: int
    hours_before: int
    scheduled_at: datetime
    title: str
    body: str
    source: str
    kind: str
    payload: dict
    idempotency_key: str


def config_from_model(config) -> AppointmentReminderConfig:
    return AppointmentReminderConfig(
        enabled=bool(getattr(config, "lembretes_agendamento_ativos", True)),
        day_before_enabled=bool(
            getattr(config, "lembrete_agendamento_1d_ativo", True)
        ),
        hours_before_enabled=bool(
            getattr(config, "lembrete_agendamento_horas_ativo", True)
        ),
        hours_before=int(
            getattr(config, "lembrete_agendamento_horas_antes", None) or 1
        ),
    )


def build_reminder_jobs(
    *,
    config: AppointmentReminderConfig,
    tenant_id,
    customer_id: int,
    appointment_id: int,
    starts_at: datetime,
    module: str,
    kind: str,
    pet_id: int | None,
    pet_name: str | None,
    title: str,
    body_for_hours: Callable[[int], str],
    now: datetime | None = None,
    idempotency_prefix: str | None = None,
) -> list[ReminderJob]:
    if not config.enabled:
        return []

    now = now or _now_like(starts_at)
    source = "appointment_reminder"
    prefix = idempotency_prefix or f"{module}-agendamento:{appointment_id}:"
    jobs: list[ReminderJob] = []

    for hours in _reminder_offsets(config):
        scheduled_at = starts_at - timedelta(hours=hours)
        if scheduled_at <= now:
            continue

        payload = {
            "source": source,
            "kind": kind,
            "module": module,
            "agendamento_id": appointment_id,
            "appointment_id": appointment_id,
            "pet_id": pet_id,
            "pet_nome": pet_name,
            "starts_at": starts_at.isoformat(),
            "hours_before": hours,
        }
        jobs.append(
            ReminderJob(
                tenant_id=tenant_id,
                customer_id=customer_id,
                appointment_id=appointment_id,
                hours_before=hours,
                scheduled_at=scheduled_at,
                title=title,
                body=body_for_hours(hours),
                source=source,
                kind=kind,
                payload=payload,
                idempotency_key=f"{prefix}{hours}h:{starts_at.isoformat()}",
            )
        )

    return jobs


def replace_pending_reminder_jobs(db, *, tenant_id, idempotency_prefix: str) -> int:
    from app.campaigns.models import NotificationQueue, NotificationStatusEnum

    return (
        db.query(NotificationQueue)
        .filter(
            NotificationQueue.tenant_id == tenant_id,
            NotificationQueue.idempotency_key.like(f"{idempotency_prefix}%"),
            NotificationQueue.status == NotificationStatusEnum.pending,
        )
        .delete(synchronize_session=False)
    )


def enqueue_reminder_jobs(db, jobs: list[ReminderJob]) -> int:
    from app.campaigns.models import NotificationChannelEnum, NotificationQueue

    enqueued = 0
    for job in jobs:
        exists = (
            db.query(NotificationQueue.id)
            .filter(NotificationQueue.idempotency_key == job.idempotency_key)
            .first()
        )
        if exists:
            continue

        db.add(
            NotificationQueue(
                tenant_id=job.tenant_id,
                idempotency_key=job.idempotency_key,
                customer_id=job.customer_id,
                channel=NotificationChannelEnum.push,
                subject=job.title,
                body=job.body,
                scheduled_at=job.scheduled_at,
                source=job.source,
                kind=job.kind,
                payload=job.payload,
            )
        )
        enqueued += 1
    return enqueued


def _reminder_offsets(config: AppointmentReminderConfig) -> list[int]:
    offsets: list[int] = []
    if config.day_before_enabled:
        offsets.append(24)
    if config.hours_before_enabled and config.hours_before > 0:
        offsets.append(int(config.hours_before))
    return sorted(set(offsets), reverse=True)


def _now_like(value: datetime) -> datetime:
    return datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
