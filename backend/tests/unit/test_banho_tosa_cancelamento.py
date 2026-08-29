from datetime import datetime, timezone
from types import SimpleNamespace

from app.banho_tosa_cancelamento import _finalizar_etapas_abertas


def test_cancelamento_finaliza_etapa_com_datetime_aware_sem_falhar():
    inicio = datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc)
    etapa = SimpleNamespace(inicio_em=inicio, fim_em=None, duracao_minutos=None)

    _finalizar_etapas_abertas([etapa], datetime(2026, 8, 28, 18, 7))

    assert etapa.fim_em.tzinfo == timezone.utc
    assert etapa.duracao_minutos == 7
