import os
from datetime import datetime, timedelta
from types import SimpleNamespace

os.environ["DEBUG"] = "false"

from app import veterinario_agendamentos as agenda
from app.veterinario_agendamentos import (
    _agendamento_intervalo,
    _agendamento_to_dict,
    _consulta_tem_conteudo_clinico,
    _sincronizar_marcos_agendamento,
)


def test_agendamento_intervalo_usa_30_minutos_por_padrao():
    inicio = datetime(2026, 4, 25, 9, 0)

    assert _agendamento_intervalo(inicio, None) == (inicio, inicio + timedelta(minutes=30))
    assert _agendamento_intervalo(inicio, 0) == (inicio, inicio + timedelta(minutes=30))
    assert _agendamento_intervalo(inicio, -5) == (inicio, inicio + timedelta(minutes=1))


def test_sincronizar_marcos_agendamento_finalizado_preenche_inicio_e_fim(monkeypatch):
    agora = datetime(2026, 4, 25, 10, 15)
    monkeypatch.setattr(agenda, "_vet_now", lambda: agora)
    agendamento = SimpleNamespace(status="finalizado", inicio_atendimento=None, fim_atendimento=None)

    _sincronizar_marcos_agendamento(agendamento)

    assert agendamento.inicio_atendimento == agora
    assert agendamento.fim_atendimento == agora


def test_sincronizar_marcos_agendamento_agendado_limpa_inicio_e_fim():
    agendamento = SimpleNamespace(
        status="agendado",
        inicio_atendimento=datetime(2026, 4, 25, 10, 0),
        fim_atendimento=datetime(2026, 4, 25, 10, 30),
    )

    _sincronizar_marcos_agendamento(agendamento)

    assert agendamento.inicio_atendimento is None
    assert agendamento.fim_atendimento is None


def test_consulta_tem_conteudo_clinico_detecta_texto_e_numero():
    assert _consulta_tem_conteudo_clinico(SimpleNamespace(historia_clinica="tutor relata dor"))
    assert _consulta_tem_conteudo_clinico(SimpleNamespace(peso_consulta=8.4))
    assert not _consulta_tem_conteudo_clinico(SimpleNamespace())


def test_agendamento_to_dict_preserva_campos_do_contrato():
    data_hora = datetime(2026, 4, 25, 14, 0)
    created_at = datetime(2026, 4, 25, 8, 0)
    agendamento = SimpleNamespace(
        id=10,
        pet_id=2,
        cliente_id=3,
        veterinario_id=4,
        consultorio_id=5,
        data_hora=data_hora,
        duracao_minutos=45,
        tipo="consulta",
        motivo="rotina",
        status="confirmado",
        is_emergencia=False,
        consulta_id=99,
        observacoes="sem jejum",
        created_at=created_at,
        pet=SimpleNamespace(nome="Mel"),
        cliente=SimpleNamespace(nome="Ana"),
        veterinario=SimpleNamespace(nome="Dra. Julia"),
        consultorio=SimpleNamespace(nome="Sala 1"),
    )

    payload = _agendamento_to_dict(agendamento)

    assert payload["id"] == 10
    assert payload["pet_nome"] == "Mel"
    assert payload["veterinario_nome"] == "Dra. Julia"
    assert payload["consultorio_nome"] == "Sala 1"
    assert payload["data_hora"] == data_hora
