from uuid import UUID

import app.services.pedido_duplicate_reconciliation_service as duplicate_service
import app.services.pedido_status_reconciliation_service as status_service
from app.tenancy.context import clear_current_tenant, get_current_tenant, set_current_tenant


TENANT_A = UUID("11111111-1111-4111-8111-111111111111")
TENANT_B = UUID("22222222-2222-4222-8222-222222222222")
PREVIOUS_TENANT = UUID("99999999-9999-4999-8999-999999999999")


def teardown_function():
    clear_current_tenant()


def test_status_reconciliation_discovers_tenants_with_authorized_global_sql(monkeypatch):
    chamadas = []

    def fake_execute(db, sql, params=None, **kwargs):
        chamadas.append({"db": db, "sql": str(sql), "params": params or {}, **kwargs})
        return [("tenant-a",), ("tenant-b",)]

    monkeypatch.setattr(status_service, "execute_tenant_safe_all", fake_execute, raising=False)

    db = object()
    resultado = status_service.listar_tenants_com_pedidos_reconciliaveis(db, dias=5)

    assert resultado == ["tenant-a", "tenant-b"]
    assert chamadas[0]["db"] is db
    assert "pedidos_integrados" in chamadas[0]["sql"]
    assert chamadas[0]["params"]["dias"] == 5
    assert chamadas[0]["require_tenant"] is False
    assert chamadas[0]["allow_global"] is True
    assert "pedidos integrados reconciliaveis" in chamadas[0]["global_reason"]


def test_status_reconciliation_batch_ativa_contexto_por_tenant(monkeypatch):
    vistos = []

    monkeypatch.setattr(
        status_service,
        "listar_tenants_com_pedidos_reconciliaveis",
        lambda *args, **kwargs: [str(TENANT_A), str(TENANT_B)],
    )

    def fake_reconciliar(db, tenant_id, **kwargs):
        vistos.append((str(tenant_id), get_current_tenant()))
        return {"tenant_id": str(tenant_id), "pedidos_processados": 0}

    monkeypatch.setattr(status_service, "reconciliar_status_pedidos_recentes", fake_reconciliar)

    set_current_tenant(PREVIOUS_TENANT)

    resultado = status_service.executar_reconciliacao_automatica_status_pedidos(
        object(),
        dias=3,
        _correlation_context_applied=True,
    )

    assert resultado["tenants_processados"] == 2
    assert vistos == [(str(TENANT_A), TENANT_A), (str(TENANT_B), TENANT_B)]
    assert get_current_tenant() == PREVIOUS_TENANT


def test_duplicate_reconciliation_discovers_tenants_with_authorized_global_sql(monkeypatch):
    chamadas = []

    def fake_execute(db, sql, params=None, **kwargs):
        chamadas.append({"db": db, "sql": str(sql), "params": params or {}, **kwargs})
        return [("tenant-a",), ("tenant-b",)]

    monkeypatch.setattr(duplicate_service, "execute_tenant_safe_all", fake_execute, raising=False)

    db = object()
    resultado = duplicate_service.listar_tenants_com_duplicidades_recentes(db, dias=4)

    assert resultado == ["tenant-a", "tenant-b"]
    assert chamadas[0]["db"] is db
    assert "pedidos_integrados" in chamadas[0]["sql"]
    assert chamadas[0]["params"]["dias"] == 4
    assert chamadas[0]["require_tenant"] is False
    assert chamadas[0]["allow_global"] is True
    assert "duplicidades de pedidos integrados" in chamadas[0]["global_reason"]


def test_duplicate_reconciliation_batch_ativa_contexto_por_tenant(monkeypatch):
    vistos = []

    monkeypatch.setattr(
        duplicate_service,
        "listar_tenants_com_duplicidades_recentes",
        lambda *args, **kwargs: [str(TENANT_A), str(TENANT_B)],
    )

    def fake_reconciliar(db, tenant_id, **kwargs):
        vistos.append((str(tenant_id), get_current_tenant()))
        return {"tenant_id": str(tenant_id), "grupos_mapeados": 0}

    monkeypatch.setattr(duplicate_service, "reconciliar_duplicidades_recentes_pedido_loja", fake_reconciliar)

    set_current_tenant(PREVIOUS_TENANT)

    resultado = duplicate_service.executar_reconciliacao_automatica_duplicidades_pedidos(
        object(),
        dias=3,
        _correlation_context_applied=True,
    )

    assert resultado["tenants_processados"] == 2
    assert vistos == [(str(TENANT_A), TENANT_A), (str(TENANT_B), TENANT_B)]
    assert get_current_tenant() == PREVIOUS_TENANT
