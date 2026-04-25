from app.veterinario_ia import _responder_chat_exame


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
