from app.formas_pagamento_routes_parts.analise_routes import (
    _classificar_margem_liquida,
)


def test_classificacao_de_margem_respeita_limites_da_empresa():
    assert (
        _classificar_margem_liquida(35, margem_saudavel=30, margem_alerta=15) == "verde"
    )
    assert (
        _classificar_margem_liquida(20, margem_saudavel=30, margem_alerta=15)
        == "amarelo"
    )
    assert (
        _classificar_margem_liquida(9, margem_saudavel=30, margem_alerta=15)
        == "vermelho"
    )


def test_classificacao_de_margem_inclui_os_limites():
    assert (
        _classificar_margem_liquida(30, margem_saudavel=30, margem_alerta=15) == "verde"
    )
    assert (
        _classificar_margem_liquida(15, margem_saudavel=30, margem_alerta=15)
        == "amarelo"
    )
