import inspect
import importlib.util
from types import SimpleNamespace

from app import vendas_routes
from app.vendas import comissoes as vendas_comissoes


def test_vendas_comissoes_module_expoe_helpers_de_reprocessamento():
    assert importlib.util.find_spec("app.vendas.comissoes") is not None


def test_vendas_schemas_module_expoe_schemas_usadas_pelo_router():
    assert importlib.util.find_spec("app.vendas.schemas") is not None

    from app.vendas import schemas as vendas_schemas

    assert vendas_routes.VendaItemSchema is vendas_schemas.VendaItemSchema
    assert vendas_routes.VendaPagamentoSchema is vendas_schemas.VendaPagamentoSchema
    assert vendas_routes.CriarVendaRequest is vendas_schemas.CriarVendaRequest
    assert vendas_routes.FinalizarVendaRequest is vendas_schemas.FinalizarVendaRequest
    assert vendas_routes.CancelarVendaRequest is vendas_schemas.CancelarVendaRequest
    assert vendas_routes.ExcluirVendaRequest is vendas_schemas.ExcluirVendaRequest
    assert vendas_routes.MarcarEntregueRequest is vendas_schemas.MarcarEntregueRequest


def test_gerar_comissoes_pendentes_ignora_parcelas_ja_geradas(monkeypatch):
    chamadas = []

    monkeypatch.setattr(
        vendas_comissoes,
        "_listar_pagamentos_venda_para_comissao",
        lambda db, venda_id, tenant_id: [
            (10, "Pix", 50, None),
            (11, "Credito", 25, None),
        ],
    )
    monkeypatch.setattr(
        vendas_comissoes,
        "_parcelas_com_comissao_funcionario",
        lambda db, venda_id, funcionario_id, tenant_id: {1},
    )

    def fake_gerar_comissoes_venda(**kwargs):
        chamadas.append(kwargs)
        return {"success": True, "total_comissao": "7.50"}

    monkeypatch.setitem(
        __import__("sys").modules,
        "app.comissoes_service",
        SimpleNamespace(gerar_comissoes_venda=fake_gerar_comissoes_venda),
    )

    venda = SimpleNamespace(id=123, funcionario_id=77)

    resultado = vendas_routes._gerar_comissoes_pendentes_venda(
        db=None,
        venda=venda,
        tenant_id="tenant-a",
        trigger="test",
    )

    assert resultado["comissoes_geradas"] == 1
    assert resultado["total_comissoes"] == 7.50
    assert len(chamadas) == 1
    assert chamadas[0]["venda_id"] == 123
    assert chamadas[0]["funcionario_id"] == 77
    assert chamadas[0]["valor_pago"] == 25
    assert chamadas[0]["forma_pagamento"] == "Credito"
    assert chamadas[0]["parcela_numero"] == 2


def test_atualizar_venda_aciona_comissoes_sem_bloquear_venda_finalizada():
    source = inspect.getsource(vendas_routes.atualizar_venda)

    assert "_gerar_comissoes_pendentes_venda(" in source
    assert "venda.status != 'finalizada'" not in source
