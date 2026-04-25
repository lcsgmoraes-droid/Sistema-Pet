from datetime import datetime
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ["DEBUG"] = "false"

from app.veterinario_clinico import _bloquear_lancamento_em_consulta_finalizada
from app.veterinario_internacao import (
    _build_payload_procedimento_agenda_internacao,
    _serializar_procedimento_agenda_internacao,
)


def _agenda_item(status="agendado"):
    return SimpleNamespace(
        id=42,
        internacao_id=7,
        pet_id=3,
        internacao=SimpleNamespace(motivo="Observacao clinica [BAIA:5]"),
        pet=SimpleNamespace(nome="Mel"),
        horario_agendado=datetime(2026, 4, 24, 10, 30),
        medicamento="Dipirona",
        dose="1 gota/kg",
        via="VO",
        quantidade_prevista=2.0,
        quantidade_executada=2.0 if status == "concluido" else None,
        quantidade_desperdicio=0.5 if status == "concluido" else None,
        unidade_quantidade="mL",
        lembrete_minutos=30,
        observacoes_agenda="Administrar apos alimentacao",
        executado_por="Dra. Ana" if status == "concluido" else None,
        horario_execucao=datetime(2026, 4, 24, 10, 35) if status == "concluido" else None,
        observacao_execucao="Sem reacao" if status == "concluido" else None,
        status=status,
        procedimento_evolucao_id=99 if status == "concluido" else None,
    )


def test_serializa_agenda_de_internacao_no_contrato_do_frontend():
    data = _serializar_procedimento_agenda_internacao(_agenda_item(status="concluido"))

    assert data["id"] == 42
    assert data["backend_id"] == 42
    assert data["internacao_id"] == 7
    assert data["pet_nome"] == "Mel"
    assert data["baia"] == "5"
    assert data["feito"] is True
    assert data["feito_por"] == "Dra. Ana"
    assert data["procedimento_evolucao_id"] == 99


def test_payload_clinico_da_agenda_nao_marca_baixa_de_estoque_automatica():
    payload = _build_payload_procedimento_agenda_internacao(_agenda_item(status="concluido"))

    assert payload["status"] == "concluido"
    assert payload["tipo_registro"] == "procedimento_agendado"
    assert payload["medicamento"] == "Dipirona"
    assert payload["horario_execucao"] == "2026-04-24T10:35:00"
    assert payload["estoque_baixado"] is False
    assert payload["estoque_movimentacao_ids"] == []


def test_consulta_finalizada_bloqueia_novos_lancamentos_satelites():
    consulta = SimpleNamespace(status="finalizada")

    with pytest.raises(HTTPException) as exc:
        _bloquear_lancamento_em_consulta_finalizada(consulta, "nova prescricao vinculada")

    assert exc.value.status_code == 409
    assert "Consulta finalizada" in exc.value.detail
