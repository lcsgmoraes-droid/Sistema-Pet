import os
from datetime import datetime, timezone

os.environ["DEBUG"] = "false"

from app.veterinario_core import _serializar_datetime_vet, _vet_now


def test_vet_now_usa_utc_com_timezone_para_persistencia():
    agora = _vet_now()

    assert agora.tzinfo is not None
    assert agora.utcoffset() == timezone.utc.utcoffset(agora)


def test_serializar_datetime_vet_exibe_utc_em_horario_brasilia():
    valor_utc = datetime(2026, 5, 17, 21, 6, tzinfo=timezone.utc)

    assert _serializar_datetime_vet(valor_utc) == datetime(2026, 5, 17, 18, 6)
