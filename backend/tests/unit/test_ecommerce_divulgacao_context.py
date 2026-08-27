from types import SimpleNamespace

from app.routes import ecommerce_aparencia_routes


class _Query:
    def __init__(self, tenant):
        self.tenant = tenant

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.tenant


class _Db:
    def __init__(self, tenant):
        self.tenant = tenant

    def query(self, *_args, **_kwargs):
        return _Query(self.tenant)


def test_tenant_context_expoe_dados_necessarios_para_artes_de_divulgacao():
    tenant = SimpleNamespace(
        id="tenant-1",
        name="Pet Shop Teste",
        ecommerce_slug="pet-shop-teste",
        status="active",
        cidade="Presidente Prudente",
        uf="SP",
        telefone="(18) 99999-0000",
        latitude=-22.12,
        longitude=-51.4,
        ecommerce_cor_primaria="#0f766e",
        ecommerce_cor_secundaria="#0f172a",
        logo_url="/uploads/ecommerce/logo.png",
        banner_1_url=None,
        banner_2_url=None,
        banner_3_url=None,
    )

    resultado = ecommerce_aparencia_routes.tenant_context_logado.__wrapped__(
        user_and_tenant=(SimpleNamespace(id=7), tenant.id),
        db=_Db(tenant),
    )

    assert resultado["storefront_path"] == "/pet-shop-teste"
    assert resultado["telefone"] == "(18) 99999-0000"
    assert resultado["ecommerce_cor_primaria"] == "#0f766e"
    assert resultado["ecommerce_cor_secundaria"] == "#0f172a"
