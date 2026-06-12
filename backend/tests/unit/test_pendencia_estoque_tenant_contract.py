from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from app.services import pendencia_estoque_service


ROOT = Path(__file__).resolve().parents[2]
TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")


class _FakeQuery:
    def __init__(self, events, first_result=None):
        self._events = events
        self._first_result = first_result

    def filter(self, *conditions):
        self._events.append(("filter", conditions))
        return self

    def order_by(self, *columns):
        self._events.append(("order_by", columns))
        return self

    def first(self):
        self._events.append("first")
        return self._first_result

    def all(self):
        self._events.append("all")
        return []


class _FakeDB:
    def __init__(self, events, first_result=None):
        self.events = events
        self.first_result = first_result
        self.committed = False
        self.rolled_back = False

    def query(self, _model):
        self.events.append("query")
        return _FakeQuery(self.events, self.first_result)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def _capture_rls_sync(monkeypatch, events):
    def fake_sync_rls_tenant(db, tenant_id):
        events.append(("sync", db, tenant_id))
        return True

    monkeypatch.setattr(
        pendencia_estoque_service,
        "sync_rls_tenant",
        fake_sync_rls_tenant,
        raising=False,
    )


def _flatten_conditions(conditions):
    for condition in conditions:
        clauses = getattr(condition, "clauses", None)
        if clauses is None:
            yield condition
        else:
            yield from _flatten_conditions(tuple(clauses))


def _has_tenant_condition(conditions):
    return any(
        getattr(getattr(condition, "left", None), "name", None) == "tenant_id"
        and str(getattr(condition, "right", "")) == ":tenant_id_1"
        for condition in _flatten_conditions(conditions)
    )


def test_verificar_e_notificar_pendencias_syncs_explicit_tenant_before_query(monkeypatch):
    events = []
    db = _FakeDB(events, first_result=None)
    _capture_rls_sync(monkeypatch, events)

    result = pendencia_estoque_service.verificar_e_notificar_pendencias(
        db=db,
        tenant_id=TENANT_ID,
        produto_id=10,
        quantidade_entrada=3,
    )

    assert result == {"sucesso": False, "erro": "Produto não encontrado"}
    assert events[:2] == [("sync", db, TENANT_ID), "query"]


def test_marcar_pendencia_finalizada_syncs_and_filters_by_explicit_tenant(monkeypatch):
    events = []
    pendencia = SimpleNamespace(
        status="pendente",
        data_finalizacao=None,
        venda_id=None,
    )
    db = _FakeDB(events, first_result=pendencia)
    _capture_rls_sync(monkeypatch, events)

    result = pendencia_estoque_service.marcar_pendencia_finalizada(
        db=db,
        pendencia_id=11,
        venda_id=22,
        tenant_id=TENANT_ID,
    )

    filter_event = next(event for event in events if isinstance(event, tuple) and event[0] == "filter")
    assert result is True
    assert events[:2] == [("sync", db, TENANT_ID), "query"]
    assert _has_tenant_condition(filter_event[1])
    assert pendencia.status == "finalizado"
    assert pendencia.venda_id == 22
    assert pendencia.data_finalizacao is not None
    assert db.committed is True


def test_dashboard_product_detail_lookup_uses_explicit_tenant_filter():
    source = (ROOT / "app" / "pendencia_estoque_routes.py").read_text(encoding="utf-8")

    dashboard_start = source.index("def dashboard_pendencias(")
    dashboard_source = source[dashboard_start:]
    query_start = dashboard_source.index("db.query(Produto)")
    query_block = dashboard_source[query_start:dashboard_source.index("if produto:", query_start)]

    assert "Produto.tenant_id == tenant" in query_block
