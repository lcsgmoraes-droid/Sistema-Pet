from types import SimpleNamespace
from uuid import uuid4

from app.estoque_alertas_routes import (
    ItemVerificarEstoque,
    VerificarEstoqueRequest,
    verificar_estoque_negativo_pre_venda,
)
from app.tenancy.context import clear_current_tenant, get_current_tenant


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result


class _Db:
    def __init__(self, product):
        self.product = product

    def query(self, *_args, **_kwargs):
        return _Query(self.product)


def test_verificar_estoque_negativo_usa_contexto_tenant_oficial():
    tenant_id = uuid4()
    clear_current_tenant()
    product = SimpleNamespace(id=10, nome="Racao teste", estoque_atual=1)
    request = VerificarEstoqueRequest(
        itens=[ItemVerificarEstoque(produto_id=10, quantidade=3)]
    )

    response = verificar_estoque_negativo_pre_venda(
        request=request,
        user_and_tenant=(SimpleNamespace(id=99), tenant_id),
        db=_Db(product),
    )

    assert len(response) == 1
    assert response[0].produto_id == 10
    assert response[0].estoque_resultante == -2
    assert get_current_tenant() == tenant_id
