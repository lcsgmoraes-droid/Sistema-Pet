from datetime import datetime, timezone
from types import SimpleNamespace

from app.banho_tosa_agenda_capacity import _calcular_pico, _duracao_minutos
from app.banho_tosa_agenda_slots import _ocupacao_recurso_no_slot


def test_ocupacao_do_slot_aceita_agendamento_com_timezone_e_slot_sem_timezone():
    agendamento = SimpleNamespace(
        recurso_id=10,
        data_hora_inicio=datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc),
        data_hora_fim_prevista=datetime(2026, 4, 26, 10, 0, tzinfo=timezone.utc),
    )

    ocupacao = _ocupacao_recurso_no_slot(
        [agendamento],
        10,
        datetime(2026, 4, 26, 9, 30),
        datetime(2026, 4, 26, 10, 30),
    )

    assert ocupacao == 1


def test_capacidade_calcula_duracao_e_pico_com_datetimes_mistos():
    inicio_com_timezone = datetime(2026, 4, 26, 9, 0, tzinfo=timezone.utc)
    fim_sem_timezone = datetime(2026, 4, 26, 10, 0)

    assert _duracao_minutos(inicio_com_timezone, fim_sem_timezone) == 60
    assert _calcular_pico(
        [
            (inicio_com_timezone, fim_sem_timezone),
            (
                datetime(2026, 4, 26, 9, 30),
                datetime(2026, 4, 26, 10, 30, tzinfo=timezone.utc),
            ),
        ]
    ) == 2
