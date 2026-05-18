import os
from datetime import datetime, timezone

os.environ["DEBUG"] = "false"

from app.veterinario_core import (
    _normalizar_datetime_local_brasilia,
    _serializar_datetime_vet,
    _vet_now,
)


def test_vet_now_usa_utc_com_timezone_para_persistencia():
    agora = _vet_now()

    assert agora.tzinfo is not None
    assert agora.utcoffset() == timezone.utc.utcoffset(agora)


def test_serializar_datetime_vet_exibe_utc_em_horario_brasilia():
    valor_utc = datetime(2026, 5, 17, 21, 6, tzinfo=timezone.utc)

    assert _serializar_datetime_vet(valor_utc) == datetime(2026, 5, 17, 18, 6)


def test_normalizar_datetime_local_brasilia_preserva_horario_digitado():
    valor_digitado = datetime(2026, 5, 18, 0, 2)

    normalizado = _normalizar_datetime_local_brasilia(valor_digitado)

    assert normalizado.tzinfo is not None
    assert _serializar_datetime_vet(normalizado) == valor_digitado
