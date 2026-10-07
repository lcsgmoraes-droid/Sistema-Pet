from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.compras_pendencias_serializacao import _iso_utc, _serializar_historico


def test_historico_explicita_utc_para_data_sem_fuso():
    item = SimpleNamespace(
        id=1,
        tipo="status_alterado",
        observacao=None,
        status_anterior="aberta",
        status_novo="resolvida",
        created_at=datetime(2026, 10, 3, 15, 44),
        user=SimpleNamespace(nome="Ana", email=None),
    )

    assert _serializar_historico(item)["created_at"] == "2026-10-03T15:44:00+00:00"
    assert _iso_utc(None) is None


def test_data_com_fuso_preserva_o_instante():
    brasilia = timezone(timedelta(hours=-3))
    value = datetime(2026, 10, 3, 12, 44, tzinfo=brasilia)

    assert datetime.fromisoformat(_iso_utc(value)) == value
