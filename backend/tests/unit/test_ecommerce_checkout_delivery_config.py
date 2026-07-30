from types import SimpleNamespace
from uuid import UUID

from app.models import ConfiguracaoEntrega, Tenant
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
    def __init__(self, delivery_config, tenant=None):
        self.delivery_config = delivery_config
        self.tenant = tenant or SimpleNamespace(
            cidade=None,
            ecommerce_entrega_ativa=True,
            ecommerce_taxa_entrega=0,
            ecommerce_frete_gratis_acima=None,
            ecommerce_prazo_entrega_texto=None,
        )
        self.queried_models = []

    def query(self, model):
        self.queried_models.append(model)
        return _Query(self.tenant if model is Tenant else self.delivery_config)

    def execute(self, *_args, **_kwargs):
        raise AssertionError("checkout delivery config must not use raw SQL")


class _ContextCheckingQuery(_Query):
    def first(self):
        assert get_current_tenant() == UUID(TENANT_ID)
        return self.result


class _ContextCheckingDb(_Db):
    def query(self, model):
        self.queried_models.append(model)
        result = self.tenant if model is Tenant else self.delivery_config
        return _ContextCheckingQuery(result)


def test_frete_local_uses_tenant_scoped_delivery_config_model():
    db = _Db(SimpleNamespace(cidade="Sao Paulo"))

    result = _frete_local_por_cidade(db, TENANT_ID, "sao paulo")

    assert db.queried_models == [ConfiguracaoEntrega, Tenant]
    assert result["cidade_loja"] == "Sao Paulo"
    assert result["cidade_destino"] == "sao paulo"


def test_frete_local_reactivates_and_restores_tenant_context_from_parameter():
    clear_current_tenant()
    db = _ContextCheckingDb(SimpleNamespace(cidade="Campinas"))

    result = _frete_local_por_cidade(db, TENANT_ID, "campinas")

    assert result["cidade_loja"] == "Campinas"
    assert get_current_tenant() is None


def test_frete_local_applies_configured_fee_and_free_shipping_threshold():
    tenant = SimpleNamespace(
        cidade="Sao Paulo",
        ecommerce_entrega_ativa=True,
        ecommerce_taxa_entrega=12.5,
        ecommerce_frete_gratis_acima=150,
        ecommerce_prazo_entrega_texto="Entrega em até 2 dias úteis",
    )
    db = _Db(SimpleNamespace(cidade=None), tenant=tenant)

    charged = _frete_local_por_cidade(db, TENANT_ID, "são paulo", subtotal=120)
    free = _frete_local_por_cidade(db, TENANT_ID, "são paulo", subtotal=180)

    assert charged["valor_frete"] == 12.5
    assert charged["prazo_estimado"] == "Entrega em até 2 dias úteis"
    assert charged["frete_gratis_aplicado"] is False
    assert free["valor_frete"] == 0
    assert free["frete_gratis_aplicado"] is True
