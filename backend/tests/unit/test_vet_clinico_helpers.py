import os
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ["DEBUG"] = "false"

from app.veterinario_clinico import (
    _aliases_especie_vet,
    _bloquear_lancamento_em_consulta_finalizada,
    _consulta_esta_finalizada,
    _idade_inicio_meses_protocolo,
    _montar_alertas_pet,
    _status_vacinal_pet,
)


class _FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return self.items


class _FakeDb:
    def __init__(self, *, protocolos=None, vacinas=None, exames=None):
        self.protocolos = protocolos or []
        self.vacinas = vacinas or []
        self.exames = exames or []

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "ProtocoloVacina":
            return _FakeQuery(self.protocolos)
        if name == "VacinaRegistro":
            return _FakeQuery(self.vacinas)
        if name == "ExameVet":
            return _FakeQuery(self.exames)
        return _FakeQuery([])


def test_consulta_esta_finalizada_normaliza_status():
    assert _consulta_esta_finalizada(SimpleNamespace(status=" FINALIZADA "))
    assert not _consulta_esta_finalizada(SimpleNamespace(status="em_atendimento"))
    assert not _consulta_esta_finalizada(None)


def test_bloqueia_lancamento_em_consulta_finalizada():
    with pytest.raises(HTTPException) as exc:
        _bloquear_lancamento_em_consulta_finalizada(
            SimpleNamespace(status="finalizada"),
            "novo procedimento vinculado",
        )

    assert exc.value.status_code == 409
    assert "Consulta finalizada" in exc.value.detail


def test_aliases_especie_e_idade_inicio_vacina():
    assert {"canino", "cao", "cão"}.issubset(_aliases_especie_vet("canino"))
    assert _idade_inicio_meses_protocolo(12) == 3.0
    assert _idade_inicio_meses_protocolo(None) is None


def test_status_vacinal_pet_monta_carteira_vencida_e_pendente():
    hoje = date.today()
    pet = SimpleNamespace(id=1, especie="canino", data_nascimento=hoje - timedelta(days=365))
    protocolos = [
        SimpleNamespace(nome="V10", especie="cao", dose_inicial_semanas=8),
        SimpleNamespace(nome="Raiva", especie="todos", dose_inicial_semanas=12),
    ]
    vacinas = [
        SimpleNamespace(
            id=10,
            nome_vacina="V10",
            data_aplicacao=hoje - timedelta(days=400),
            data_proxima_dose=hoje - timedelta(days=5),
            numero_dose=1,
            lote="L1",
            fabricante="Lab",
        )
    ]

    status = _status_vacinal_pet(_FakeDb(protocolos=protocolos, vacinas=vacinas), pet, "tenant-a")

    assert status["resumo"] == {"total_aplicadas": 1, "total_pendentes": 1, "total_vencidas": 1}
    assert status["carteira"][0]["status"] == "atrasada"
    assert status["pendentes"][0]["nome"] == "Raiva"
    assert status["pendentes"][0]["idade_inicio_meses"] == 3.0


def test_montar_alertas_pet_inclui_alergia_vacina_e_exame():
    hoje = date.today()
    pet = SimpleNamespace(
        id=1,
        especie="canino",
        data_nascimento=hoje - timedelta(days=365),
        alergias_lista=["dipirona"],
        alergias="",
        restricoes_alimentares_lista=["sem frango"],
    )
    vacinas = [
        SimpleNamespace(
            id=10,
            nome_vacina="V10",
            data_aplicacao=hoje - timedelta(days=400),
            data_proxima_dose=hoje - timedelta(days=5),
            numero_dose=1,
            lote="L1",
            fabricante="Lab",
        )
    ]
    exames = [SimpleNamespace(nome="Hemograma", status="solicitado")]

    alertas = _montar_alertas_pet(_FakeDb(vacinas=vacinas, exames=exames), pet, "tenant-a")

    tipos = {alerta["tipo"] for alerta in alertas}
    assert {"alergia", "restricao", "vacina_atrasada", "exame_pendente"}.issubset(tipos)
