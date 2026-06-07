import pytest
from fastapi import HTTPException

from app.produtos.validators import (
    _obter_produto_ou_404,
    _validar_codigo_barras_unico,
    _validar_pode_inativar_produto,
    _validar_sku_unico,
    _validar_tenant_e_obter_usuario,
)


class FakeQuery:
    def __init__(self, *, first_result=None, count_result=0):
        self.first_result = first_result
        self.count_result = count_result
        self.filters = []

    def filter(self, *conditions):
        self.filters.append(conditions)
        return self

    def first(self):
        return self.first_result

    def count(self):
        return self.count_result


class FakeDb:
    def __init__(self, query):
        self.query_instance = query
        self.queried_models = []

    def query(self, model):
        self.queried_models.append(model)
        return self.query_instance


class ProdutoFake:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_validar_tenant_e_obter_usuario_desempacota_contexto():
    assert _validar_tenant_e_obter_usuario(("usuario", 7)) == ("usuario", 7)


def test_obter_produto_ou_404_retorna_produto_existente():
    produto = ProdutoFake(id=1)

    assert _obter_produto_ou_404(FakeDb(FakeQuery(first_result=produto)), 1, 10) is produto


def test_obter_produto_ou_404_dispara_404_quando_nao_encontra():
    with pytest.raises(HTTPException) as exc_info:
        _obter_produto_ou_404(FakeDb(FakeQuery(first_result=None)), 1, 10)

    assert exc_info.value.status_code == 404


def test_validar_sku_unico_aceita_sku_livre():
    _validar_sku_unico(FakeDb(FakeQuery(first_result=None)), "SKU-1", 10)


def test_validar_sku_unico_bloqueia_duplicado():
    with pytest.raises(HTTPException) as exc_info:
        _validar_sku_unico(FakeDb(FakeQuery(first_result=ProdutoFake(id=2))), "SKU-1", 10)

    assert exc_info.value.status_code == 400
    assert "SKU-1" in exc_info.value.detail


def test_validar_codigo_barras_unico_bloqueia_duplicado():
    with pytest.raises(HTTPException) as exc_info:
        _validar_codigo_barras_unico(
            FakeDb(FakeQuery(first_result=ProdutoFake(id=2))),
            "7891234567890",
            10,
        )

    assert exc_info.value.status_code == 400
    assert "7891234567890" in exc_info.value.detail


def test_validar_pode_inativar_produto_bloqueia_pai_com_variacao_ativa():
    produto = ProdutoFake(id=1, nome="Produto Pai", is_parent=True)

    with pytest.raises(HTTPException) as exc_info:
        _validar_pode_inativar_produto(
            FakeDb(FakeQuery(count_result=2)),
            produto,
            10,
        )

    assert exc_info.value.status_code == 409
    assert "Produto Pai" in exc_info.value.detail


def test_validar_pode_inativar_produto_ignora_produto_sem_variacoes():
    produto = ProdutoFake(id=1, nome="Produto", is_parent=False)

    _validar_pode_inativar_produto(FakeDb(FakeQuery(count_result=2)), produto, 10)
