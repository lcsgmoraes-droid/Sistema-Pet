import pytest
from fastapi import HTTPException

from app.produtos.core import (
    _aplicar_status_ativo_produto,
    _nome_indica_granel,
    _normalizar_filtro_ativo_produtos,
    _normalizar_payload_granel,
    _normalizar_promocao_erp_payload,
    _normalizar_sku_produto,
    _produto_sku_value,
)


class ProdutoFake:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_normalizar_sku_produto_limpa_e_usa_caixa_alta():
    assert _normalizar_sku_produto(" abc-123 ") == "ABC-123"


def test_normalizar_sku_produto_bloqueia_vazio():
    with pytest.raises(HTTPException) as exc_info:
        _normalizar_sku_produto(" ")

    assert exc_info.value.status_code == 400
    assert "obrigatorio" in exc_info.value.detail


def test_normalizar_filtro_ativo_respeita_incluir_inativos():
    assert _normalizar_filtro_ativo_produtos(True, False) is True
    assert _normalizar_filtro_ativo_produtos(False, False) is False
    assert _normalizar_filtro_ativo_produtos(True, True) is None


def test_normalizar_promocao_payload_marca_ativo_por_preco_promocional():
    assert (
        _normalizar_promocao_erp_payload({"preco_promocional": "12.90"})[
            "promocao_ativa"
        ]
        is True
    )
    assert (
        _normalizar_promocao_erp_payload({"preco_promocional": ""})["promocao_ativa"]
        is False
    )


def test_normalizar_promocao_payload_preserva_edicao_sem_campos_de_promocao():
    dados = {"nome": "Produto"}
    produto = ProdutoFake(preco_promocional=10)

    assert _normalizar_promocao_erp_payload(dados, produto) is dados
    assert "promocao_ativa" not in dados


def test_normalizar_payload_granel_por_flag_ou_nome():
    normalizado = _normalizar_payload_granel({"nome": "Racao a granel"})

    assert normalizado["e_granel"] is True
    assert normalizado["tipo_produto"] == "SIMPLES"
    assert normalizado["unidade"] == "KG"
    assert normalizado["participa_sugestao_compra"] is False
    assert _nome_indica_granel("Areia Granel") is True


def test_aplicar_status_ativo_desliga_canais_quando_inativo():
    produto = ProdutoFake(
        ativo=True,
        situacao=True,
        anunciar_ecommerce=True,
        anunciar_app=True,
        updated_at=None,
    )

    _aplicar_status_ativo_produto(produto, False)

    assert produto.ativo is False
    assert produto.situacao is False
    assert produto.anunciar_ecommerce is False
    assert produto.anunciar_app is False
    assert produto.updated_at is not None


def test_produto_sku_value_lida_com_campo_ausente():
    assert _produto_sku_value(ProdutoFake(sku="ABC")) == "ABC"
    assert _produto_sku_value(ProdutoFake()) is None
