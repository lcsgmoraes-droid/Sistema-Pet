import os
from types import SimpleNamespace

os.environ["DEBUG"] = "false"

from app.veterinario_ia import (
    _montar_resposta_dose,
    _montar_resposta_interacao,
    _normalizar_modo_ia,
    _responder_chat_exame,
)


def _chat(**overrides):
    base = {
        "pergunta": "resumo",
        "exame_nome": "Hemograma",
        "tipo_exame": "laboratorial",
        "especie": "canino",
        "nome_pet": "Thor",
        "alergias": [],
        "alertas": [],
        "resumo_ia": "",
        "conclusao_ia": "",
        "dados_json": {},
        "texto_resultado": "",
        "payload_ia": {},
        "tem_arquivo": False,
    }
    base.update(overrides)
    return _responder_chat_exame(**base)


def test_chat_exame_pede_resultado_quando_resumo_sem_dados():
    resposta = _chat(pergunta="resumo")

    assert "ainda não tem resultado registrado" in resposta


def test_chat_exame_destaca_alertas_clinicos():
    resposta = _chat(
        pergunta="tem alerta grave?",
        alertas=[{"campo": "creatinina", "mensagem": "Creatinina acima do esperado"}],
        resumo_ia="Creatinina alta",
    )

    assert "Pontos de atenção" in resposta
    assert "Creatinina acima do esperado" in resposta


def test_chat_exame_responde_parametros_renais_estruturados():
    resposta = _chat(
        pergunta="como está a creatinina renal?",
        dados_json={"creatinina": 2.1, "ureia": 72},
        resumo_ia="Alteração renal leve",
    )

    assert "- creatinina: 2.1" in resposta
    assert "Alteração renal leve" in resposta


def test_chat_exame_orienta_processamento_quando_arquivo_sem_interpretacao():
    resposta = _chat(
        pergunta="me ajude",
        tem_arquivo=True,
        texto_resultado="",
        dados_json={},
    )

    assert "Processar arquivo + IA" in resposta


def test_normalizar_modo_ia_restringe_valores_validos():
    assert _normalizar_modo_ia("atendimento") == "atendimento"
    assert _normalizar_modo_ia("qualquer coisa") == "livre"


def test_resposta_dose_calcula_faixa_mgkg():
    med = SimpleNamespace(
        nome="Amoxicilina",
        nome_comercial="",
        principio_ativo="amoxicilina",
        dose_min_mgkg=10,
        dose_max_mgkg=20,
    )

    resposta = _montar_resposta_dose("qual dose de amoxicilina?", [med], 5, "canino")

    assert "10.00 a 20.00 mg/kg" in resposta
    assert "50.00 mg a 100.00 mg" in resposta


def test_resposta_interacao_detecta_principio_duplicado():
    meds = [
        SimpleNamespace(
            nome="Med A",
            nome_comercial="",
            principio_ativo="dipirona",
            interacoes="",
        ),
        SimpleNamespace(
            nome="Med B",
            nome_comercial="",
            principio_ativo="dipirona",
            interacoes="",
        ),
    ]

    resposta = _montar_resposta_interacao("pode associar?", meds, "Med A", "Med B")

    assert "mesmo princípio ativo" in resposta
    assert "duplicidade terapêutica" in resposta
