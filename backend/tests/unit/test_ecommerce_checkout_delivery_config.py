from types import SimpleNamespace
from uuid import UUID

from app.models import ConfiguracaoEntrega
from app.routes.ecommerce_checkout import _frete_local_por_cidade
from app.tenancy.context import clear_current_tenant, get_current_tenant


TENANT_ID = "11111111-1111-1111-1111-111111111111"


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result


class _Db:
    def __init__(self, delivery_config):
        self.delivery_config = delivery_config
        self.queried_models = []

    def query(self, model):
        self.queried_models.append(model)
        return _Query(self.delivery_config)

    def execute(self, *_args, **_kwargs):
        raise AssertionError("checkout delivery config must not use raw SQL")


class _ContextCheckingQuery(_Query):
    def first(self):
        assert get_current_tenant() == UUID(TENANT_ID)
        return self.result


class _ContextCheckingDb(_Db):
    def query(self, model):
        self.queried_models.append(model)
        return _ContextCheckingQuery(self.delivery_config)


def test_frete_local_uses_tenant_scoped_delivery_config_model():
    db = _Db(SimpleNamespace(cidade="Sao Paulo"))

    result = _frete_local_por_cidade(db, TENANT_ID, "sao paulo")

    assert db.queried_models == [ConfiguracaoEntrega]
    assert result["cidade_loja"] == "Sao Paulo"
    assert result["cidade_destino"] == "sao paulo"


def test_frete_local_reactivates_and_restores_tenant_context_from_parameter():
    clear_current_tenant()
    db = _ContextCheckingDb(SimpleNamespace(cidade="Campinas"))

    result = _frete_local_por_cidade(db, TENANT_ID, "campinas")

    assert result["cidade_loja"] == "Campinas"
    assert get_current_tenant() is None
