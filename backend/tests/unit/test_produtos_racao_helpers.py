from app.produtos.racao import (
    _normalizar_classificacao_racao,
    _normalizar_payload_racao,
    _produto_eh_racao_expr,
)


def test_normalizar_classificacao_racao_preserva_aliases_operacionais():
    assert _normalizar_classificacao_racao(None) is None
    assert _normalizar_classificacao_racao("") is None
    assert _normalizar_classificacao_racao("Super Premium") == "super_premium"
    assert _normalizar_classificacao_racao("super-premium") == "super_premium"
    assert _normalizar_classificacao_racao("Terapêutica") == "terapeutica"
    assert _normalizar_classificacao_racao("Especial Premium") == "especial"
    assert _normalizar_classificacao_racao("grain free") == "grain free"


def test_normalizar_payload_racao_limpa_campos_quando_desmarca_racao():
    dados = {
        "eh_racao": False,
        "classificacao_racao": "premium",
        "peso_embalagem": 15,
        "categoria_racao": "cao",
        "linha_racao_id": 10,
        "porte_animal_id": 20,
    }

    normalizado = _normalizar_payload_racao(dados)

    assert "eh_racao" not in normalizado
    assert normalizado["tipo"] == "produto"
    assert normalizado["classificacao_racao"] is None
    assert normalizado["peso_embalagem"] is None
    assert normalizado["categoria_racao"] is None
    assert normalizado["linha_racao_id"] is None
    assert normalizado["porte_animal_id"] is None


def test_normalizar_payload_racao_inferido_por_classificacao():
    normalizado = _normalizar_payload_racao({"classificacao_racao": "Premium"})

    assert normalizado["tipo"] == "ração"
    assert normalizado["classificacao_racao"] == "premium"


def test_normalizar_payload_racao_aceita_sim_nao_herdados():
    assert _normalizar_payload_racao({"classificacao_racao": "sim"}) == {
        "classificacao_racao": None,
        "tipo": "ração",
    }
    assert _normalizar_payload_racao({"classificacao_racao": "não"})[
        "tipo"
    ] == "produto"


def test_produto_eh_racao_expr_is_sql_expression():
    expr = _produto_eh_racao_expr()

    assert hasattr(expr, "compile")

