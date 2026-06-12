from types import SimpleNamespace
from uuid import UUID

from app.estoque import service as estoque_service
from app.estoque.service import EstoqueService
from app import vendas_models  # noqa: F401


TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")


class _FakeQuery:
    def __init__(self, events, first_result=None):
        self._events = events
        self._first_result = first_result

    def filter(self, *conditions):
        self._events.append(("filter", conditions))
        return self

    def first(self):
        self._events.append("first")
        return self._first_result


class _FakeDB:
    def __init__(self, events, first_result=None):
        self.events = events
        self.first_result = first_result
        self.added = []
        self.flushed = False

    def query(self, _model):
        self.events.append("query")
        return _FakeQuery(self.events, self.first_result)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed = True


def _capture_rls_sync(monkeypatch, events):
    def fake_sync_rls_tenant(db, tenant_id):
        events.append(("sync", db, tenant_id))
        return True

    monkeypatch.setattr(
        estoque_service,
        "sync_rls_tenant",
        fake_sync_rls_tenant,
        raising=False,
    )


def test_registrar_alerta_estoque_negativo_syncs_explicit_tenant_before_query(monkeypatch):
    events = []
    db = _FakeDB(events, first_result=SimpleNamespace(permite_estoque_negativo=True))
    produto = SimpleNamespace(id=77, nome="Racao especial")
    _capture_rls_sync(monkeypatch, events)

    EstoqueService._validar_ou_registrar_estoque_negativo(
        produto=produto,
        quantidade=5,
        estoque_anterior=2,
        tenant_id=TENANT_ID,
        referencia_id=123,
        referencia_tipo="venda",
        documento="VENDA-123",
        db=db,
    )

    assert events[:2] == [("sync", db, TENANT_ID), "query"]
    assert len(db.added) == 1
    assert db.added[0].tenant_id == TENANT_ID
    assert db.added[0].produto_id == 77
    assert db.added[0].estoque_resultante == -3
    assert db.added[0].venda_id == 123
    assert db.flushed is True
