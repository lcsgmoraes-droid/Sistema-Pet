from types import SimpleNamespace
from uuid import UUID

import app.services.nfe_authorized_reconciliation_service as service
from app.services.nfe_authorized_reconciliation_service import (
    executar_reconciliacao_automatica_nfes_autorizadas,
    listar_tenants_com_nfes_autorizadas_recentes,
    reconciliar_nf_autorizada_cache,
)
from app.middlewares.request_context import clear_request_context, get_request_id
from app.tenancy.context import (
    clear_current_tenant,
    get_current_tenant,
    set_current_tenant,
)
from app.utils.logger import clear_context


def teardown_function():
    clear_request_context()
    clear_current_tenant()
    clear_context()


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
    def __init__(self, itens, movimentos=None):
        self.itens = itens
        self.movimentos = movimentos or []
        self.flush_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.added = []

    def query(self, model):
        nome = getattr(model, "__name__", "")
        if nome == "PedidoIntegrado":
            return _FakeQuery(first_result=None)
        if nome == "PedidoIntegradoItem":
            return _FakeQuery(all_result=self.itens)
        if nome == "EstoqueMovimentacao":
            return _FakeQuery(
                all_result=self.movimentos, count_result=len(self.movimentos)
            )
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
    db = _FakeDB([item], movimentos=[])
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
        lambda **kwargs: (
            capturado.setdefault("processou_nf", kwargs),
            "venda_confirmada",
        )[1],
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


def test_reconciliar_nf_autorizada_cache_reprocessa_quando_so_existe_baixa_legada(
    monkeypatch,
):
    pedido = SimpleNamespace(
        id=1225,
        tenant_id="tenant-1",
        pedido_bling_id="25441648396",
        pedido_bling_numero="11733",
        status="confirmado",
        payload={"ultima_nf": {"id": "25441651001", "numero": "011088"}},
    )
    item = SimpleNamespace(sku="019516.1/1", vendido_em="2026-03-30T22:28:21")
    registro = SimpleNamespace(
        bling_id="25441651448",
        numero="011089",
        numero_pedido_loja="260331HQ17M377",
        pedido_bling_id_ref="25441648396",
        detalhe_payload={
            "numero": "011089",
            "numeroPedidoLoja": "260331HQ17M377",
            "situacao": 5,
        },
        resumo_payload={},
        status="Autorizada",
    )
    movimento_legado = SimpleNamespace(
        produto_id=6359,
        documento="11733",
        observacao="Baixa automatica via webhook Bling (Atendido)",
        status="confirmado",
    )
    db = _FakeDB([item], movimentos=[movimento_legado])
    capturado = {}

    monkeypatch.setattr(
        "app.integracao_bling_nf_routes._localizar_pedido_local_por_numero_loja",
        lambda *args, **kwargs: pedido,
    )
    monkeypatch.setattr(
        "app.integracao_bling_nf_routes._localizar_pedido_local_por_numero_bling",
        lambda *args, **kwargs: pedido,
    )
    monkeypatch.setattr(
        "app.integracao_bling_nf_routes._registrar_nf_no_pedido",
        lambda **kwargs: capturado.setdefault("registrou_nf", kwargs),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.processar_nf_autorizada",
        lambda **kwargs: (
            capturado.setdefault("processou_nf", kwargs),
            "venda_confirmada",
        )[1],
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
    assert capturado["processou_nf"]["nf_id"] == "25441651448"


def test_executar_reconciliacao_automatica_nfes_autorizadas_inclui_correlacao(
    monkeypatch,
):
    monkeypatch.setattr(
        service,
        "listar_tenants_com_nfes_autorizadas_recentes",
        lambda *args, **kwargs: [],
    )

    resultado = executar_reconciliacao_automatica_nfes_autorizadas(object(), dias=3)

    assert resultado["correlation_id"].startswith("job.nfe-authorized-reconciliation-")
    assert get_request_id() is None


def test_executar_reconciliacao_automatica_nfes_autorizadas_ativa_contexto_por_tenant(
    monkeypatch,
):
    tenant_a = UUID("33333333-3333-4333-8333-333333333333")
    tenant_b = UUID("44444444-4444-4444-8444-444444444444")
    previous_tenant = UUID("99999999-9999-4999-8999-999999999999")
    vistos = []

    monkeypatch.setattr(
        service,
        "listar_tenants_com_nfes_autorizadas_recentes",
        lambda *args, **kwargs: [str(tenant_a), str(tenant_b)],
    )

    def fake_reconciliar(db, tenant_id, **kwargs):
        vistos.append((str(tenant_id), get_current_tenant()))
        return {
            "tenant_id": str(tenant_id),
            "notas_reconciliadas": 0,
        }

    monkeypatch.setattr(
        service, "reconciliar_nfes_autorizadas_recentes", fake_reconciliar
    )

    set_current_tenant(previous_tenant)

    resultado = executar_reconciliacao_automatica_nfes_autorizadas(
        object(),
        dias=3,
        _correlation_context_applied=True,
    )

    assert resultado["tenants_processados"] == 2
    assert vistos == [(str(tenant_a), tenant_a), (str(tenant_b), tenant_b)]
    assert get_current_tenant() == previous_tenant


def test_listar_tenants_com_nfes_autorizadas_recentes_usa_sql_global_autorizado(
    monkeypatch,
):
    chamadas = []

    def fake_execute(db, sql, params=None, **kwargs):
        chamadas.append({"db": db, "sql": sql, "params": params or {}, **kwargs})
        return [("tenant-a",), ("tenant-b",)]

    monkeypatch.setattr(
        service, "_garantir_registry_sqlalchemy_reconciliacao", lambda: None
    )
    monkeypatch.setattr(service, "execute_tenant_safe_all", fake_execute, raising=False)

    db = object()
    resultado = listar_tenants_com_nfes_autorizadas_recentes(db, dias=5)

    assert resultado == ["tenant-a", "tenant-b"]
    assert chamadas[0]["db"] is db
    assert "bling_notas_fiscais_cache" in chamadas[0]["sql"]
    assert chamadas[0]["require_tenant"] is False
    assert chamadas[0]["allow_global"] is True
    assert chamadas[0]["global_reason"]
