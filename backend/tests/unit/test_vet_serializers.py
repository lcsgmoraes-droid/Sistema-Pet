import os
from datetime import date, datetime
from types import SimpleNamespace

os.environ["DEBUG"] = "false"

from app.veterinario_serializers import (
    _consulta_to_dict,
    _hash_prontuario_consulta,
    _prescricao_to_dict,
)


def _consulta(**overrides):
    base = {
        "id": 7,
        "pet_id": 2,
        "cliente_id": 3,
        "veterinario_id": 4,
        "tipo": "consulta",
        "status": "finalizada",
        "queixa_principal": "coceira",
        "historia_clinica": "relato do tutor",
        "peso_consulta": 8.2,
        "temperatura": 38.5,
        "frequencia_cardiaca": 100,
        "frequencia_respiratoria": 24,
        "tpc": "2s",
        "mucosas": "normocoradas",
        "hidratacao": "normal",
        "nivel_dor": 1,
        "saturacao_o2": 98,
        "pressao_sistolica": 120,
        "pressao_diastolica": 80,
        "glicemia": 90,
        "exame_fisico": "sem alteracoes graves",
        "hipotese_diagnostica": "dermatite",
        "diagnostico": "dermatite alergica",
        "diagnostico_simples": "dermatite",
        "conduta": "medicacao e retorno",
        "retorno_em_dias": 10,
        "data_retorno": date(2026, 5, 5),
        "asa_score": 1,
        "asa_justificativa": "",
        "observacoes_internas": "",
        "observacoes_tutor": "retornar se piorar",
        "hash_prontuario": "abc",
        "finalizado_em": datetime(2026, 4, 25, 11, 0),
        "inicio_atendimento": datetime(2026, 4, 25, 10, 30),
        "fim_atendimento": datetime(2026, 4, 25, 11, 0),
        "pet": SimpleNamespace(nome="Mel"),
        "cliente": SimpleNamespace(nome="Ana"),
        "veterinario": SimpleNamespace(nome="Dra. Julia"),
        "created_at": datetime(2026, 4, 25, 10, 0),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_consulta_to_dict_preserva_contrato_principal():
    payload = _consulta_to_dict(_consulta())

    assert payload["id"] == 7
    assert payload["pet_nome"] == "Mel"
    assert payload["cliente_nome"] == "Ana"
    assert payload["veterinario_nome"] == "Dra. Julia"
    assert payload["diagnostico"] == "dermatite alergica"
    assert payload["finalizado_em"] == datetime(2026, 4, 25, 11, 0)


def test_hash_prontuario_consulta_e_deterministico():
    consulta = _consulta(hash_prontuario=None)

    primeiro = _hash_prontuario_consulta(consulta)
    segundo = _hash_prontuario_consulta(consulta)

    assert primeiro == segundo
    assert len(primeiro) == 64


def test_prescricao_to_dict_serializa_itens():
    prescricao = SimpleNamespace(
        id=4,
        consulta_id=7,
        pet_id=2,
        veterinario_id=4,
        numero="REC-00004",
        data_emissao=date(2026, 4, 25),
        tipo_receituario="simples",
        observacoes="apos refeicao",
        hash_receita="hash",
        created_at=datetime(2026, 4, 25, 12, 0),
        itens=[
            SimpleNamespace(
                id=9,
                nome_medicamento="Dipirona",
                concentracao="500mg",
                forma_farmaceutica="comprimido",
                quantidade="10",
                posologia="1 comprimido",
                via_administracao="VO",
                duracao_dias=5,
                medicamento_catalogo_id=33,
            )
        ],
    )

    payload = _prescricao_to_dict(prescricao)

    assert payload["numero"] == "REC-00004"
    assert payload["itens"][0]["nome_medicamento"] == "Dipirona"
    assert payload["itens"][0]["medicamento_catalogo_id"] == 33
