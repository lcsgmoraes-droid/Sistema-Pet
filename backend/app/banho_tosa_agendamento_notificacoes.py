from __future__ import annotations

from app.banho_tosa_api.utils import STATUS_AGENDAMENTO_FINAIS
from app.banho_tosa_models import BanhoTosaAgendamento
from app.services.appointment_reminders import (
    build_reminder_jobs,
    config_from_model,
    enqueue_reminder_jobs,
    replace_pending_reminder_jobs,
)


def sincronizar_lembretes_agendamento_banho_tosa(
    db, *, tenant_id, agendamento: BanhoTosaAgendamento, config
) -> None:
    if (
        not agendamento.id
        or not agendamento.cliente_id
        or not agendamento.data_hora_inicio
    ):
        return

    prefixo = f"banho-tosa-agendamento:{agendamento.id}:"
    replace_pending_reminder_jobs(db, tenant_id=tenant_id, idempotency_prefix=prefixo)

    if (
        agendamento.status in STATUS_AGENDAMENTO_FINAIS
        or agendamento.status != "agendado"
    ):
        return

    pet_nome = getattr(getattr(agendamento, "pet", None), "nome", None)
    jobs = build_reminder_jobs(
        config=config_from_model(config),
        tenant_id=tenant_id,
        customer_id=agendamento.cliente_id,
        appointment_id=agendamento.id,
        starts_at=agendamento.data_hora_inicio,
        module="banho_tosa",
        kind="banho_tosa_agendamento",
        pet_id=agendamento.pet_id,
        pet_name=pet_nome,
        title="Lembrete de Banho & Tosa",
        body_for_hours=lambda horas: _mensagem_lembrete_banho_tosa(
            agendamento, pet_nome, horas
        ),
        idempotency_prefix=prefixo,
    )
    enqueue_reminder_jobs(db, jobs)


def _mensagem_lembrete_banho_tosa(
    agendamento: BanhoTosaAgendamento, pet_nome: str | None, horas: int
) -> str:
    pet_label = pet_nome or "Seu pet"
    horario = agendamento.data_hora_inicio.strftime("%H:%M")
    if horas >= 24:
        return f"{pet_label} tem Banho & Tosa agendado para amanha as {horario}."
    if horas == 1:
        return f"{pet_label} tem Banho & Tosa agendado em 1 hora ({horario})."
    return f"{pet_label} tem Banho & Tosa agendado em {horas} horas ({horario})."
