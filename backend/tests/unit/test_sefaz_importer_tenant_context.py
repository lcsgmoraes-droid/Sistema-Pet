from types import SimpleNamespace
from uuid import UUID

import app.notas_entrada.sefaz_importer as importer
from app.tenancy.context import (
    clear_current_tenant,
    get_current_tenant,
    set_current_tenant,
)


TARGET_TENANT = UUID("11111111-1111-4111-8111-111111111111")
PREVIOUS_TENANT = UUID("99999999-9999-4999-8999-999999999999")


def teardown_function():
    clear_current_tenant()


class _QueryRecorder:
    def __init__(self, seen_contexts):
        self._seen_contexts = seen_contexts

    def filter(self, *args):
        self._seen_contexts.append(get_current_tenant())
        return self

    def order_by(self, *args):
        self._seen_contexts.append(get_current_tenant())
        return self

    def first(self):
        self._seen_contexts.append(get_current_tenant())
        return SimpleNamespace(id=10)


class _DBRecorder:
    def __init__(self):
        self.seen_contexts = []

    def query(self, *args):
        self.seen_contexts.append(get_current_tenant())
        return _QueryRecorder(self.seen_contexts)


def test_importar_docs_sefaz_ativa_contexto_do_tenant_durante_consultas(monkeypatch):
    monkeypatch.setattr(
        importer.SefazTenantConfigService,
        "load_config",
        lambda tenant_id: {"cnpj": "12.345.678/0001-90"},
    )

    db = _DBRecorder()
    set_current_tenant(PREVIOUS_TENANT)

    resultado = importer.importar_docs_sefaz([], str(TARGET_TENANT), db)

    assert resultado["importadas"] == 0
    assert db.seen_contexts
    assert set(db.seen_contexts) == {TARGET_TENANT}
    assert get_current_tenant() == PREVIOUS_TENANT
