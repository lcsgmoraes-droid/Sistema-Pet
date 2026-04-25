import os
from datetime import datetime

import pytest
from pydantic import ValidationError

os.environ["DEBUG"] = "false"

from app.veterinario_schemas import (
    AgendamentoCreate,
    CatalogoCreate,
    InternacaoConfigUpdate,
    PrescricaoCreate,
    ProcedimentoAgendaInternacaoCreate,
    ProcedimentoCreate,
    VetMensagemFeedbackPayload,
)


def test_agendamento_create_defaults_principais():
    payload = AgendamentoCreate(pet_id=1, data_hora=datetime(2026, 4, 25, 9, 0))

    assert payload.tipo == "consulta"
    assert payload.duracao_minutos == 30
    assert payload.is_emergencia is False


def test_prescricao_create_converte_itens_aninhados():
    payload = PrescricaoCreate(
        consulta_id=1,
        pet_id=2,
        itens=[{"nome_medicamento": "Dipirona", "posologia": "1 comprimido"}],
    )

    assert payload.itens[0].nome_medicamento == "Dipirona"
    assert payload.tipo_receituario == "simples"


def test_schemas_com_listas_usam_default_factory_independente():
    procedimento_a = ProcedimentoCreate(consulta_id=1, nome="Aplicação")
    procedimento_b = ProcedimentoCreate(consulta_id=1, nome="Curativo")
    catalogo = CatalogoCreate(nome="Vacina")

    procedimento_a.insumos.append({"produto_id": 1})

    assert procedimento_b.insumos == []
    assert catalogo.insumos == []


def test_validacoes_de_limite_preservadas():
    with pytest.raises(ValidationError):
        InternacaoConfigUpdate(total_baias=0)

    with pytest.raises(ValidationError):
        ProcedimentoAgendaInternacaoCreate(
            horario_agendado=datetime(2026, 4, 25, 9, 0),
            medicamento="Dipirona",
            lembrete_min=2000,
        )

    with pytest.raises(ValidationError):
        VetMensagemFeedbackPayload(util=True, nota=6)
