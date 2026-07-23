from datetime import datetime, timezone
from types import SimpleNamespace

from app.veterinario_calendar import formatar_datetime_ics, gerar_calendario_ics


def test_formatar_datetime_ics_preserva_horario_de_parede():
    data = datetime(2026, 7, 23, 14, 30, tzinfo=timezone.utc)

    assert formatar_datetime_ics(data) == "20260723T143000"


def test_gerar_calendario_ics_declara_timezone_de_brasilia():
    agendamento = SimpleNamespace(
        id=7,
        data_hora=datetime(2026, 7, 23, 14, 30, tzinfo=timezone.utc),
        duracao_minutos=45,
        pet=SimpleNamespace(nome="Luna"),
        pet_id=1,
        cliente=SimpleNamespace(nome="Ana"),
        veterinario=SimpleNamespace(nome="Dra. Bia"),
        consultorio=SimpleNamespace(nome="Sala 1"),
        tipo="consulta",
        status="confirmado",
        motivo="Retorno",
        observacoes=None,
    )

    conteudo = gerar_calendario_ics(
        [agendamento],
        nome_calendario="Agenda Veterinária",
    )

    assert "DTSTART;TZID=America/Sao_Paulo:20260723T143000" in conteudo
    assert "DTEND;TZID=America/Sao_Paulo:20260723T151500" in conteudo
    assert "DTSTART:20260723T143000Z" not in conteudo
