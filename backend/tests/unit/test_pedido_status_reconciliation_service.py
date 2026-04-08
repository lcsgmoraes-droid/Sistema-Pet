from types import SimpleNamespace
from unittest.mock import Mock

import app.services.pedido_status_reconciliation_service as service


def test_reconciliar_status_pedidos_recentes_retorna_sem_execucao_quando_nao_ha_pedidos(monkeypatch):
    monkeypatch.setattr(service, "_contar_pedidos_recentes_reconciliaveis", lambda *args, **kwargs: 0)
    monkeypatch.setattr(service, "_buscar_pedidos_recentes_reconciliaveis", lambda *args, **kwargs: [])

    resultado = service.reconciliar_status_pedidos_recentes(object(), "tenant-1", dias=7, limite_pedidos=50)

    assert resultado["executada"] is False
    assert resultado["motivo"] == "sem_pedidos_reconciliaveis_recentes"
    assert resultado["pedidos_processados"] == 0


def test_reconciliar_status_pedido_local_cancelado_reaplica_cancelamento(monkeypatch):
    db = Mock()
    pedido = SimpleNamespace(
        id=10,
        tenant_id="tenant-1",
        pedido_bling_id="BL-10",
        status="confirmado",
        payload={},
    )
    item = SimpleNamespace(sku="SKU-1")
    cancelamentos = []
    sincronizacoes_nf = []

    monkeypatch.setattr(
        service,
        "_consultar_pedido_bling",
        lambda pedido_bling_id: {"id": pedido_bling_id, "situacao": {"id": 12}},
    )
    monkeypatch.setattr(service, "_carregar_itens_pedido", lambda *args, **kwargs: [item])
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes._sincronizar_nf_do_pedido",
        lambda **kwargs: (sincronizacoes_nf.append(kwargs), {"numero": "011200"})[1],
    )

    def fake_cancelar_pedido(*, db, pedido, itens, processed_at=None):
        cancelamentos.append((pedido.id, len(itens)))
        pedido.status = "cancelado"

    monkeypatch.setattr("app.integracao_bling_pedido_routes._cancelar_pedido", fake_cancelar_pedido)
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes._confirmar_pedido",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("nao deveria confirmar")),
    )

    resultado = service.reconciliar_status_pedido_local(db, pedido)

    assert resultado["success"] is True
    assert resultado["acao"] == "cancelado"
    assert resultado["nf_numero"] == "011200"
    assert pedido.status == "cancelado"
    assert cancelamentos == [(10, 1)]
    assert sincronizacoes_nf[0]["enriquecer_via_api"] is True


def test_reconciliar_status_pedido_local_confirmado_reaplica_confirmacao_sem_baixa(monkeypatch):
    db = Mock()
    pedido = SimpleNamespace(
        id=11,
        tenant_id="tenant-1",
        pedido_bling_id="BL-11",
        status="aberto",
        payload={},
    )
    item = SimpleNamespace(sku="SKU-2")
    confirmacoes = []
    sincronizacoes_nf = []

    monkeypatch.setattr(
        service,
        "_consultar_pedido_bling",
        lambda pedido_bling_id: {"id": pedido_bling_id, "situacao": {"id": 9}},
    )
    monkeypatch.setattr(service, "_carregar_itens_pedido", lambda *args, **kwargs: [item])
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes._sincronizar_nf_do_pedido",
        lambda **kwargs: (sincronizacoes_nf.append(kwargs), {"numero": "011201"})[1],
    )

    def fake_confirmar_pedido(*, db, pedido, itens, motivo, observacao, processed_at=None, aplicar_baixa_estoque=False):
        confirmacoes.append(
            {
                "pedido_id": pedido.id,
                "itens": len(itens),
                "motivo": motivo,
                "aplicar_baixa_estoque": aplicar_baixa_estoque,
            }
        )
        pedido.status = "confirmado"
        return []

    monkeypatch.setattr("app.integracao_bling_pedido_routes._confirmar_pedido", fake_confirmar_pedido)
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes._cancelar_pedido",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("nao deveria cancelar")),
    )

    resultado = service.reconciliar_status_pedido_local(db, pedido)

    assert resultado["success"] is True
    assert resultado["acao"] == "confirmado"
    assert resultado["nf_numero"] == "011201"
    assert pedido.status == "confirmado"
    assert confirmacoes == [
        {
            "pedido_id": 11,
            "itens": 1,
            "motivo": "pedido_status_reconciliation",
            "aplicar_baixa_estoque": False,
        }
    ]
    assert sincronizacoes_nf[0]["enriquecer_via_api"] is True


def test_reconciliar_status_pedidos_recentes_agrega_resultados(monkeypatch):
    pedido_a = SimpleNamespace(id=1, pedido_bling_id="A")
    pedido_b = SimpleNamespace(id=2, pedido_bling_id="B")

    monkeypatch.setattr(service, "_contar_pedidos_recentes_reconciliaveis", lambda *args, **kwargs: 2)
    monkeypatch.setattr(service, "_buscar_pedidos_recentes_reconciliaveis", lambda *args, **kwargs: [pedido_a, pedido_b])
    monkeypatch.setattr(
        service,
        "reconciliar_status_pedido_local",
        lambda db, pedido: {"acao": "confirmado" if pedido.id == 1 else "cancelado", "success": True, "executada": True},
    )

    resultado = service.reconciliar_status_pedidos_recentes(object(), "tenant-1", dias=7, limite_pedidos=50)

    assert resultado["executada"] is True
    assert resultado["pedidos_processados"] == 2
    assert resultado["confirmados"] == 1
    assert resultado["cancelados"] == 1
    assert resultado["sem_mudanca"] == 0
