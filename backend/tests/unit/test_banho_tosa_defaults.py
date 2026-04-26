from app.banho_tosa_defaults import (
    PARAMETROS_PORTE_PADRAO,
    RECURSOS_PADRAO,
    SERVICOS_PADRAO,
    TEMPLATES_RETORNO_PADRAO,
)


def test_base_padrao_nao_tem_chaves_duplicadas():
    portes = [item[0] for item in PARAMETROS_PORTE_PADRAO]
    servicos = [item[0].lower() for item in SERVICOS_PADRAO]
    recursos = [(item[0].lower(), item[1]) for item in RECURSOS_PADRAO]
    templates = [(item[0].lower(), item[2]) for item in TEMPLATES_RETORNO_PADRAO]

    assert len(portes) == len(set(portes))
    assert len(servicos) == len(set(servicos))
    assert len(recursos) == len(set(recursos))
    assert len(templates) == len(set(templates))


def test_base_padrao_cobre_operacao_minima():
    assert len(PARAMETROS_PORTE_PADRAO) >= 5
    assert len(SERVICOS_PADRAO) >= 6
    assert len(RECURSOS_PADRAO) >= 4
    assert any(item[1] == "secador" and item[3] for item in RECURSOS_PADRAO)
