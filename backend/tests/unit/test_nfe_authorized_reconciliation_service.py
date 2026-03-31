from types import SimpleNamespace

from app.services.nfe_authorized_reconciliation_service import (
    reconciliar_nf_autorizada_cache,
)


class _FakeQuery:
    def __init__(self, *, first_result=None, all_result=None, count_result=0):
        self._first_result = first_result
        self._all_result = all_result or []
        self._count_result = count_result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._all_result)

    def first(self):
        return self._first_result

    def count(self):
        return int(self._count_result)


class _FakeDB:
    def __init__(self, itens, movimentos_count):
        self.itens = itens
        self.movimentos_count = movimentos_count
        self.flush_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.added = []

    def query(self, model):
        nome = getattr(model, "__name__", "")
        if nome == "PedidoIntegradoItem":
            return _FakeQuery(all_result=self.itens)
        if nome == "EstoqueMovimentacao":
            return _FakeQuery(count_result=self.movimentos_count)
        raise AssertionError(f"Modelo inesperado na query: {nome}")

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flush_calls += 1

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1


def test_reconciliar_nf_autorizada_cache_vincula_por_numero_pedido_loja(monkeypatch):
    pedido = SimpleNamespace(
        id=1245,
        tenant_id="tenant-1",
        pedido_bling_id="25443299914",
        pedido_bling_numero="11753",
        status="confirmado",
        payload={"ultima_nf": {"id": "-1"}},
    )
    item = SimpleNamespace(sku="019516.1/1", vendido_em=None)
    registro = SimpleNamespace(
        bling_id="25443301147",
        numero="011100",
        numero_pedido_loja="260331JFWD1VMB",
        pedido_bling_id_ref=None,
        detalhe_payload={
            "numero": "011100",
            "numeroPedidoLoja": "260331JFWD1VMB",
            "situacao": 5,
        },
        resumo_payload={},
        status="Autorizada",
    )
    db = _FakeDB([item], movimentos_count=0)
    capturado = {}

    monkeypatch.setattr(
        "app.integracao_bling_nf_routes._localizar_pedido_local_por_numero_loja",
        lambda *args, **kwargs: pedido,
    )
    monkeypatch.setattr(
        "app.integracao_bling_nf_routes._localizar_pedido_local_por_numero_bling",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.integracao_bling_nf_routes._registrar_nf_no_pedido",
        lambda **kwargs: capturado.setdefault("registrou_nf", kwargs),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.processar_nf_autorizada",
        lambda **kwargs: capturado.setdefault("processou_nf", kwargs) or "venda_confirmada",
    )
    monkeypatch.setattr(
        "app.services.bling_flow_monitor_service.registrar_vinculo_nf_pedido",
        lambda **kwargs: capturado.setdefault("vinculo_nf", kwargs),
    )
    monkeypatch.setattr(
        "app.services.bling_flow_monitor_service.resolver_incidentes_relacionados",
        lambda *args, **kwargs: 1,
    )
    monkeypatch.setattr(
        "app.services.bling_flow_monitor_service.registrar_evento",
        lambda **kwargs: capturado.setdefault("evento", kwargs),
    )

    resultado = reconciliar_nf_autorizada_cache(
        db,
        tenant_id="tenant-1",
        registro=registro,
    )

    assert resultado["success"] is True
    assert resultado["motivo"] == "reconciliada"
    assert registro.pedido_bling_id_ref == "25443299914"
    assert capturado["registrou_nf"]["nf_id"] == "25443301147"
    assert capturado["processou_nf"]["nf_id"] == "25443301147"
    assert capturado["vinculo_nf"]["nf_numero"] == "011100"
    assert db.commit_calls == 1
