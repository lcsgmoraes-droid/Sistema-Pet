from types import SimpleNamespace

from app.calculadora_racao import (
    _avaliar_aptidao_calculadora,
    _campos_bloqueantes_calculadora,
)


def _produto(**overrides):
    base = {
        "tipo": "produto",
        "classificacao_racao": "sim",
        "peso_embalagem": 15,
        "preco_venda": 120,
        "linha_racao_id": None,
        "porte_animal_id": None,
        "fase_publico_id": None,
        "tipo_tratamento_id": None,
        "sabor_proteina_id": None,
        "porte_animal": None,
        "fase_publico": None,
        "tipo_tratamento": None,
        "sabor_proteina": None,
        "categoria_racao": None,
        "especies_indicadas": None,
        "tabela_consumo": '{"tipo":"filhote_peso_adulto","dados":{"15kg":{"adulto":250}}}',
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_calculadora_bloqueia_peso_preco_e_tabela_obrigatorios():
    produto = _produto()

    assert _campos_bloqueantes_calculadora(produto) == []
    assert "tabela de consumo" not in _avaliar_aptidao_calculadora(produto)


def test_calculadora_informa_bloqueio_quando_falta_peso_ou_preco():
    produto = _produto(peso_embalagem=None, preco_venda=0, tabela_consumo=None)

    assert _campos_bloqueantes_calculadora(produto) == [
        "peso da embalagem",
        "preco de venda",
        "tabela de consumo",
    ]


def test_calculadora_aceita_peso_e_preco_de_fallback_do_item_selecionado():
    produto = _produto(peso_embalagem=None, preco_venda=0)

    assert (
        _campos_bloqueantes_calculadora(
            produto,
            peso_fallback=15,
            preco_fallback=120,
        )
        == []
    )


def test_calculadora_bloqueia_produto_sem_tabela_consumo():
    produto = _produto(tabela_consumo=None)

    assert _campos_bloqueantes_calculadora(produto) == ["tabela de consumo"]


def test_calculadora_permite_quantidade_manual_sem_tabela_consumo():
    produto = _produto(tabela_consumo=None)

    assert (
        _campos_bloqueantes_calculadora(
            produto,
            exigir_tabela_consumo=False,
        )
        == []
    )
