from app.produtos.search import (
    _build_produto_search_order_clause,
    _produto_search_conditions,
    _produto_search_conditions_fast,
)


def test_busca_de_produtos_inclui_gtin_comercial_e_tributario():
    expressao_completa = str(_produto_search_conditions("7898242030076"))
    expressao_rapida = str(_produto_search_conditions_fast("7898242030076"))

    assert "gtin_ean" in expressao_completa
    assert "gtin_ean_tributario" in expressao_completa
    assert "codigos_barras_alternativos" in expressao_completa
    assert "gtin_ean" in expressao_rapida
    assert "gtin_ean_tributario" in expressao_rapida
    assert "codigos_barras_alternativos" in expressao_rapida


def test_ordenacao_de_busca_prioriza_todos_os_eans_cadastrados():
    expressao_ordenacao = " ".join(
        str(clausula) for clausula in _build_produto_search_order_clause("0186361")
    )

    assert "gtin_ean" in expressao_ordenacao
    assert "gtin_ean_tributario" in expressao_ordenacao
    assert "codigos_barras_alternativos" in expressao_ordenacao


def test_busca_rapida_encontra_palavra_interna_do_sku_com_espacos():
    expressao = _produto_search_conditions_fast("TESTE")
    primeira_condicao = list(expressao.clauses)[0]

    assert primeira_condicao.left.name == "codigo"
    assert primeira_condicao.right.value == "%TESTE%"
