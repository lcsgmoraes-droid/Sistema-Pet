from pathlib import Path
from types import SimpleNamespace

from app.services.tenant_email_settings import resolve_tenant_reply_to


class _FakeQuery:
    def __init__(self, tenant):
        self.tenant = tenant

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.tenant


class _FakeSession:
    def __init__(self, tenant):
        self.tenant = tenant

    def query(self, *args, **kwargs):
        return _FakeQuery(self.tenant)


def test_reply_to_prefers_dedicated_tenant_email():
    tenant = SimpleNamespace(
        email_resposta="compras@petshop.com.br",
        email="contato@petshop.com.br",
    )

    assert (
        resolve_tenant_reply_to(_FakeSession(tenant), "tenant-a")
        == "compras@petshop.com.br"
    )


def test_reply_to_falls_back_to_company_email():
    tenant = SimpleNamespace(email_resposta=None, email="contato@petshop.com.br")

    assert (
        resolve_tenant_reply_to(_FakeSession(tenant), "tenant-a")
        == "contato@petshop.com.br"
    )


def test_reply_to_ignores_invalid_addresses_and_can_be_unconfigured():
    tenant = SimpleNamespace(email_resposta="invalido", email="tambem-invalido")

    assert resolve_tenant_reply_to(_FakeSession(tenant), "tenant-a") is None
    assert resolve_tenant_reply_to(_FakeSession(None), "tenant-a") is None


def test_supplier_email_routes_apply_tenant_reply_to():
    backend_app = Path(__file__).resolve().parents[2] / "app"
    route_paths = (
        backend_app / "pedidos_compra" / "envio_routes.py",
        backend_app / "compras_pendencias_email_routes.py",
        backend_app / "estoque_transferencia_parceiro_routes.py",
    )

    for route_path in route_paths:
        source = route_path.read_text(encoding="utf-8")
        assert "reply_to=resolve_tenant_reply_to(db, tenant_id)" in source
