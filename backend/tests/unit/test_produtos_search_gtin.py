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
