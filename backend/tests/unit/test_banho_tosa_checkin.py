from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.banho_tosa_api import agenda_routes


class _QueryResultado:
    def __init__(self, resultado):
        self.resultado = resultado

    def options(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.resultado


class _DbComResultados:
    def __init__(self, *resultados):
        self.resultados = iter(resultados)

    def query(self, *args, **kwargs):
        return _QueryResultado(next(self.resultados))


def test_checkin_bloqueia_pet_que_ja_esta_na_fila(monkeypatch):
    agendamento = SimpleNamespace(
        id=42,
        pet_id=7,
        pet=SimpleNamespace(nome="Luna"),
        status="agendado",
    )
    atendimento_ativo = SimpleNamespace(id=91, status="em_secagem")
    db = _DbComResultados(agendamento, atendimento_ativo)
    monkeypatch.setattr(
        agenda_routes,
        "_get_tenant",
        lambda current: (SimpleNamespace(id=1), "tenant-demo"),
    )

    with pytest.raises(HTTPException) as erro:
        agenda_routes.realizar_checkin_agendamento(
            agendamento_id=agendamento.id,
            db=db,
            current=object(),
        )

    assert erro.value.status_code == 409
    assert erro.value.detail == "Luna ja esta em atendimento na fila do Banho & Tosa."
