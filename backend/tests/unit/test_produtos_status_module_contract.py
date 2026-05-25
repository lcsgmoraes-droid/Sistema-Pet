from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.produtos.status import aplicar_status_ativo_produto, validar_pode_inativar_produto


class _Column:
    def __eq__(self, other):
        return ("eq", other)


class _ProdutoModel:
    produto_pai_id = _Column()
    tenant_id = _Column()
    ativo = _Column()


class _Query:
    def __init__(self, count_result):
        self.count_result = count_result
        self.filters = None

    def filter(self, *filters):
        self.filters = filters
        return self

    def count(self):
        return self.count_result


class _Db:
    def __init__(self, count_result):
        self.query_obj = _Query(count_result)

    def query(self, model):
        assert model is _ProdutoModel
        return self.query_obj


def test_validar_pode_inativar_produto_ignora_produto_que_nao_e_pai():
    produto = SimpleNamespace(is_parent=False)
    db = _Db(count_result=99)

    validar_pode_inativar_produto(db, produto, tenant_id=1, produto_model=_ProdutoModel)

    assert db.query_obj.filters is None


def test_validar_pode_inativar_produto_bloqueia_pai_com_variacoes_ativas():
    produto = SimpleNamespace(id=10, nome="Produto Pai", is_parent=True)

    with pytest.raises(HTTPException) as exc_info:
        validar_pode_inativar_produto(
            _Db(count_result=2),
            produto,
            tenant_id=1,
            produto_model=_ProdutoModel,
        )

    assert exc_info.value.status_code == 409
    assert "Produto Pai" in exc_info.value.detail
    assert "2" in exc_info.value.detail


def test_aplicar_status_ativo_produto_desliga_canais_ao_inativar():
    agora = datetime(2026, 5, 25, 14, 0)
    produto = SimpleNamespace(
        ativo=True,
        situacao=True,
        anunciar_ecommerce=True,
        anunciar_app=True,
        updated_at=None,
    )

    aplicar_status_ativo_produto(produto, False, agora_provider=lambda: agora)

    assert produto.ativo is False
    assert produto.situacao is False
    assert produto.anunciar_ecommerce is False
    assert produto.anunciar_app is False
    assert produto.updated_at == agora


def test_aplicar_status_ativo_produto_mantem_canais_ao_reativar():
    agora = datetime(2026, 5, 25, 15, 0)
    produto = SimpleNamespace(
        ativo=False,
        situacao=False,
        anunciar_ecommerce=False,
        anunciar_app=False,
        updated_at=None,
    )

    aplicar_status_ativo_produto(produto, True, agora_provider=lambda: agora)

    assert produto.ativo is True
    assert produto.situacao is True
    assert produto.anunciar_ecommerce is False
    assert produto.anunciar_app is False
    assert produto.updated_at == agora
