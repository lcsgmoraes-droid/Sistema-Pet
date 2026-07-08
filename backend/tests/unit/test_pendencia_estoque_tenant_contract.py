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


class _ModelQuery:
    def __init__(self, *, first_result=None, all_result=None):
        self._first_result = first_result
        self._all_result = all_result or []

    def filter(self, *conditions):
        return self

    def order_by(self, *columns):
        return self

    def first(self):
        return self._first_result

    def all(self):
        return self._all_result


class _WaitlistDB:
    def __init__(self, *, produto, pendencias, cliente=None, user=None, devices=None):
        self.produto = produto
        self.pendencias = pendencias
        self.cliente = cliente
        self.user = user
        self.devices = devices or []
        self.committed = False

    def query(self, model):
        if model.__name__ == "Produto":
            return _ModelQuery(first_result=self.produto)
        if model.__name__ == "PendenciaEstoque":
            return _ModelQuery(all_result=self.pendencias)
        if model.__name__ == "Cliente":
            return _ModelQuery(first_result=self.cliente)
        if model.__name__ == "User":
            return _ModelQuery(first_result=self.user)
        if model.__name__ == "UserPushDevice":
            return _ModelQuery(all_result=self.devices)
        return _ModelQuery()

    def commit(self):
        self.committed = True


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


def test_verificar_e_notificar_pendencias_syncs_explicit_tenant_before_query(
    monkeypatch,
):
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


def test_verificar_e_notificar_pendencias_notifica_cliente_do_pdv_no_app_mobile(
    monkeypatch,
):
    push_calls = []

    def fake_post(url, json, timeout, headers=None):
        push_calls.append(
            {"url": url, "json": json, "timeout": timeout, "headers": headers}
        )
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"data": {"status": "ok", "id": "ticket-stock-1"}},
        )

    monkeypatch.setattr(
        "app.services.pendencia_estoque_service.requests.post", fake_post
    )

    cliente = SimpleNamespace(
        id=77,
        user_id=5,
        nome="Lucas Guerra de Moraes",
        email="lcsgmoraes@gmail.com",
        telefone=None,
        celular=None,
    )
    pendencia = SimpleNamespace(
        id=51,
        cliente=cliente,
        status="pendente",
        quantidade_desejada=1,
        data_notificacao=None,
        whatsapp_enviado=False,
        data_finalizacao=None,
        motivo_cancelamento=None,
    )
    produto = SimpleNamespace(
        id=10,
        nome="Racao Teste",
        codigo="RACAO-TESTE",
        preco_venda=42.9,
    )
    device = SimpleNamespace(
        id=9,
        user_id=5,
        tenant_id=TENANT_ID,
        expo_push_token="ExponentPushToken[phone-a]",
        enabled=True,
        last_success_at=None,
        last_ticket_id=None,
        last_error=None,
        last_error_at=None,
    )
    db = _WaitlistDB(
        produto=produto,
        pendencias=[pendencia],
        cliente=cliente,
        user=SimpleNamespace(id=5, tenant_id=TENANT_ID, push_token=None),
        devices=[device],
    )
    _capture_rls_sync(monkeypatch, [])

    result = pendencia_estoque_service.verificar_e_notificar_pendencias(
        db=db,
        tenant_id=TENANT_ID,
        produto_id=10,
        quantidade_entrada=3,
    )

    assert result["notificacoes_enviadas"] == 1
    assert pendencia.status == "notificado"
    assert pendencia.data_notificacao is not None
    assert pendencia.data_finalizacao is None
    assert pendencia.whatsapp_enviado is False
    assert push_calls[0]["json"]["to"] == "ExponentPushToken[phone-a]"
    assert push_calls[0]["json"]["title"] == "Produto disponivel"
    assert push_calls[0]["json"]["data"] == {
        "source": "stock_waitlist",
        "kind": "stock_available",
        "produto_id": 10,
        "product_id": 10,
    }
    assert device.last_ticket_id == "ticket-stock-1"
    assert device.last_error is None
    assert db.committed is True


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

    filter_event = next(
        event for event in events if isinstance(event, tuple) and event[0] == "filter"
    )
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
    query_block = dashboard_source[
        query_start : dashboard_source.index("if produto:", query_start)
    ]

    assert "Produto.tenant_id == tenant" in query_block
