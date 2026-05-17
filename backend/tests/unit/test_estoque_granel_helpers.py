from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.estoque.granel import (
    _normalizar_produto_granel,
    _produto_e_granel,
    _serializar_vinculo_granel,
    _validar_produto_origem_granel,
)


def test_produto_e_granel_considera_flag_ou_nome():
    assert _produto_e_granel(None) is False
    assert _produto_e_granel(SimpleNamespace(e_granel=True, nome="Produto comum")) is True
    assert _produto_e_granel(SimpleNamespace(e_granel=False, nome="Racao a granel")) is True
    assert _produto_e_granel(SimpleNamespace(e_granel=False, nome="Racao pacote")) is False


def test_normalizar_produto_granel_preserva_simples_e_remove_kit():
    produto = SimpleNamespace(
        e_granel=False,
        unidade="UN",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
    )

    _normalizar_produto_granel(produto)

    assert produto.e_granel is True
    assert produto.unidade == "KG"
    assert produto.tipo_produto == "SIMPLES"
    assert produto.tipo_kit is None


def test_validar_produto_origem_granel_rejeita_origem_invalida():
    with pytest.raises(HTTPException) as ausente:
        _validar_produto_origem_granel(None)
    assert ausente.value.status_code == 404

    with pytest.raises(HTTPException) as granel:
        _validar_produto_origem_granel(
            SimpleNamespace(e_granel=True, nome="Produto granel", tipo_produto="SIMPLES")
        )
    assert granel.value.status_code == 400

    with pytest.raises(HTTPException) as sem_peso:
        _validar_produto_origem_granel(
            SimpleNamespace(
                e_granel=False,
                nome="Racao pacote",
                tipo_produto="SIMPLES",
                peso_embalagem=0,
            )
        )
    assert sem_peso.value.status_code == 400


def test_validar_produto_origem_granel_retorna_peso_pacote():
    peso = _validar_produto_origem_granel(
        SimpleNamespace(
            e_granel=False,
            nome="Racao pacote",
            tipo_produto="SIMPLES",
            peso_embalagem="15",
        )
    )

    assert peso == pytest.approx(15.0)


def test_serializar_vinculo_granel_calcula_custo_por_kg():
    origem = SimpleNamespace(
        nome="Racao pacote",
        codigo="PKG",
        estoque_atual=3,
        preco_venda=120,
        peso_embalagem=15,
        preco_custo=90,
    )
    granel = SimpleNamespace(
        nome="Racao granel",
        codigo="GR",
        estoque_atual=4.5,
        preco_venda=12,
    )
    vinculo = SimpleNamespace(
        id=55,
        ativo=True,
        produto_origem_id=1,
        produto_origem=origem,
        produto_granel_id=2,
        produto_granel=granel,
        observacao="teste",
        created_at=datetime(2026, 5, 16, 10, 0),
        updated_at=datetime(2026, 5, 16, 11, 0),
    )

    serializado = _serializar_vinculo_granel(vinculo)

    assert serializado["produto_origem_codigo"] == "PKG"
    assert serializado["produto_granel_codigo"] == "GR"
    assert serializado["peso_por_unidade_kg"] == pytest.approx(15.0)
    assert serializado["custo_por_kg"] == pytest.approx(6.0)
