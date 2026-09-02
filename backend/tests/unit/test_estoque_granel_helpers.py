from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.estoque import granel as granel_module
from app.estoque.granel import (
    _alterar_preco_venda_granel_com_historico,
    _normalizar_produto_granel,
    _produto_e_granel,
    _serializar_vinculo_granel,
    _validar_produto_origem_granel,
)


class _FakeDb:
    def __init__(self):
        self.adicionados = []

    def add(self, item):
        self.adicionados.append(item)


def test_produto_e_granel_considera_flag_ou_nome():
    assert _produto_e_granel(None) is False
    assert (
        _produto_e_granel(SimpleNamespace(e_granel=True, nome="Produto comum")) is True
    )
    assert (
        _produto_e_granel(SimpleNamespace(e_granel=False, nome="Racao a granel"))
        is True
    )
    assert (
        _produto_e_granel(SimpleNamespace(e_granel=False, nome="Racao pacote")) is False
    )


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
            SimpleNamespace(
                e_granel=True, nome="Produto granel", tipo_produto="SIMPLES"
            )
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


def test_alterar_preco_venda_granel_registra_escolha_no_historico(monkeypatch):
    monkeypatch.setattr(
        granel_module,
        "ProdutoHistoricoPreco",
        lambda **campos: SimpleNamespace(**campos),
    )
    db = _FakeDb()
    produto = SimpleNamespace(id=38, preco_custo=10.0, preco_venda=15.0)

    alterou = _alterar_preco_venda_granel_com_historico(
        db=db,
        tenant_id="tenant-aumigos",
        current_user=SimpleNamespace(id=44),
        produto_granel=produto,
        preco_venda_anterior=15.0,
        preco_custo_anterior=9.5,
        preco_venda_novo=15.2,
        conversao_id=84,
    )

    assert alterou is True
    assert produto.preco_venda == pytest.approx(15.2)
    assert len(db.adicionados) == 1
    historico = db.adicionados[0]
    assert historico.produto_id == 38
    assert historico.preco_venda_anterior == pytest.approx(15.0)
    assert historico.preco_venda_novo == pytest.approx(15.2)
    assert historico.motivo == "conversao_granel"
    assert historico.referencia == "Conversao granel #84"
    assert historico.user_id == 44
    assert str(historico.tenant_id) == "tenant-aumigos"


def test_alterar_preco_venda_granel_nao_grava_quando_valor_em_centavos_e_igual():
    db = _FakeDb()
    produto = SimpleNamespace(id=4, preco_custo=10.0, preco_venda=15.4455)

    alterou = _alterar_preco_venda_granel_com_historico(
        db=db,
        tenant_id="tenant-aumigos",
        current_user=SimpleNamespace(id=44),
        produto_granel=produto,
        preco_venda_anterior=15.4455,
        preco_custo_anterior=10.0,
        preco_venda_novo=15.45,
        conversao_id=86,
    )

    assert alterou is False
    assert produto.preco_venda == pytest.approx(15.4455)
    assert db.adicionados == []
