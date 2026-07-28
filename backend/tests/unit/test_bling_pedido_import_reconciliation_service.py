from types import SimpleNamespace
from uuid import UUID

from app.services import bling_pedido_import_reconciliation_service as service


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
