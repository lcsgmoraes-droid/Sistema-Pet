from types import SimpleNamespace
from uuid import UUID

import pytest

from app.services import bling_pedido_import_reconciliation_service as service
from app.tenancy.context import get_current_tenant, set_current_tenant


class _FakeAPI:
    def __init__(self):
        self.calls = []

    def listar_pedidos_vendas(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "data": [
                {"id": "AMZ-1", "situacao": {"id": 12}},
                {"id": "SHP-2", "situacao": {"id": 12}},
                {"id": "ML-3", "situacao": {"id": 9}},
            ]
        }


@pytest.mark.parametrize(
    "tenant_anterior",
    [None, UUID("22222222-2222-2222-2222-222222222222")],
)
@pytest.mark.parametrize("falha_na_construcao", [False, True])
def test_cliente_bling_usa_tenant_configurado_e_restaura_contexto(
    monkeypatch, tenant_anterior, falha_na_construcao
):
    tenant_id = UUID("11111111-1111-1111-1111-111111111111")
    if tenant_anterior:
        set_current_tenant(tenant_anterior)
    chamadas = []

    class APIComContexto:
        def __init__(self):
            assert get_current_tenant() == tenant_id
            chamadas.append("construcao")
            if falha_na_construcao:
                raise ValueError("credenciais indisponiveis")

        def listar_pedidos_vendas(self, **kwargs):
            assert get_current_tenant() == tenant_id
            chamadas.append("consulta")
            return {"data": []}

    monkeypatch.setattr(service, "_tenant_bling_configurado", lambda: tenant_id)
    monkeypatch.setattr("app.bling_integration.BlingAPI", APIComContexto)

    if falha_na_construcao:
        with pytest.raises(ValueError, match="credenciais indisponiveis"):
            service.reconciliar_importacao_pedidos_bling_recentes(SimpleNamespace())
        assert chamadas == ["construcao"]
    else:
        resultado = service.reconciliar_importacao_pedidos_bling_recentes(
            SimpleNamespace()
        )
        assert resultado["success"] is True
        assert resultado["avaliados"] == 0
        assert chamadas == ["construcao", "consulta"]

    assert get_current_tenant() == tenant_anterior


def test_reconciliacao_importa_ausente_e_atualiza_status_divergente(monkeypatch):
    tenant_id = UUID("11111111-1111-1111-1111-111111111111")
    api = _FakeAPI()
    processados = []
    existentes = {
        "SHP-2": SimpleNamespace(status="aberto"),
        "ML-3": SimpleNamespace(status="confirmado"),
    }

    monkeypatch.setattr(service, "_tenant_bling_configurado", lambda: tenant_id)
    monkeypatch.setattr(
        "app.bling_integration.BlingAPI",
        lambda: api,
    )
    monkeypatch.setattr(
        service,
        "localizar_pedido_por_bling_id",
        lambda db, pedido_bling_id, **kwargs: existentes.get(pedido_bling_id),
    )
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes.processar_pedido_bling_payload",
        lambda body, db: processados.append(body) or {"status": "ok"},
    )

    resultado = service.reconciliar_importacao_pedidos_bling_recentes(
        SimpleNamespace(rollback=lambda: None),
        dias=7,
        limite_paginas=2,
    )

    assert resultado["success"] is True
    assert resultado["avaliados"] == 3
    assert resultado["importados"] == 1
    assert resultado["atualizados"] == 1
    assert resultado["ignorados"] == 1
    assert [item["event"] for item in processados] == [
        "order.created",
        "order.updated",
    ]
    assert (
        api.calls[0]["data_alteracao_inicial"] <= api.calls[0]["data_alteracao_final"]
    )


def test_reconciliacao_nao_executa_sem_tenant_bling(monkeypatch):
    monkeypatch.setattr(service, "_tenant_bling_configurado", lambda: None)

    resultado = service.reconciliar_importacao_pedidos_bling_recentes(SimpleNamespace())

    assert resultado == {
        "success": False,
        "executada": False,
        "motivo": "bling_webhook_tenant_nao_configurado",
    }


def test_reconciliacao_reprocessa_confirmado_com_item_ainda_reservado(monkeypatch):
    tenant_id = UUID("11111111-1111-1111-1111-111111111111")
    api = _FakeAPI()
    api.listar_pedidos_vendas = lambda **kwargs: {
        "data": [{"id": "ML-3", "situacao": {"id": 9}}]
    }
    pedido = SimpleNamespace(id=30, status="confirmado")
    processados = []

    monkeypatch.setattr(service, "_tenant_bling_configurado", lambda: tenant_id)
    monkeypatch.setattr("app.bling_integration.BlingAPI", lambda: api)
    monkeypatch.setattr(
        service,
        "localizar_pedido_por_bling_id",
        lambda *args, **kwargs: pedido,
    )
    monkeypatch.setattr(
        service,
        "_pedido_confirmado_possui_itens_pendentes",
        lambda db, pedido_arg: pedido_arg is pedido,
    )
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes.processar_pedido_bling_payload",
        lambda body, db: processados.append(body) or {"status": "ok"},
    )

    resultado = service.reconciliar_importacao_pedidos_bling_recentes(
        SimpleNamespace(rollback=lambda: None)
    )

    assert resultado["atualizados"] == 1
    assert resultado["ignorados"] == 0
    assert [item["event"] for item in processados] == ["order.updated"]
