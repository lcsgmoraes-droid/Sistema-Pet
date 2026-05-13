from types import SimpleNamespace
from uuid import uuid4

from app.empresa_config_routes import get_config_empresa


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _FakeSession:
    def query(self, *args, **kwargs):
        return _FakeQuery()


def test_get_config_empresa_usa_tenant_da_dependencia_multitenant():
    user = SimpleNamespace(id=1, email="smoke@teste.local")
    tenant_id = uuid4()

    response = get_config_empresa(
        user_and_tenant=(user, tenant_id),
        db=_FakeSession(),
    )

    assert response.id == 0
    assert response.margem_saudavel_minima == 30.0
