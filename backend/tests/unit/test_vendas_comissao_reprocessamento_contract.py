import inspect
import importlib.util
from decimal import Decimal
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
    venda = SimpleNamespace(id=123, funcionario_id=77)
    monkeypatch.setattr(
        vendas_comissoes,
        "_bloquear_venda_para_comissao",
        lambda *_args: venda,
    )

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


def test_geracao_rele_pagamentos_sob_lock_apos_commit_de_cada_comissao(monkeypatch):
    venda = SimpleNamespace(id=123, funcionario_id=77)
    ordem = []
    chamadas = []
    pagamentos = [
        (10, "Pix", 50, None, 99, "confirmado"),
        (11, "Credito", 25, None, 100, "confirmado"),
    ]

    def bloquear(*_args):
        ordem.append("lock")
        return venda

    def listar(*_args):
        ordem.append("ler")
        return pagamentos

    def gerar(**kwargs):
        chamadas.append(kwargs)
        ordem.append("commit")
        # Simula estorno confirmado por outra requisição entre o commit da
        # primeira comissão e o início da geração da próxima parcela.
        pagamentos.append((12, "Credito", -25, None, 100, "confirmado"))
        return {"success": True, "total_comissao": "5"}

    monkeypatch.setattr(vendas_comissoes, "_bloquear_venda_para_comissao", bloquear)
    monkeypatch.setattr(
        vendas_comissoes, "_listar_pagamentos_venda_para_comissao", listar
    )
    monkeypatch.setattr(
        vendas_comissoes, "_parcelas_com_comissao_funcionario", lambda *_args: set()
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.comissoes_service",
        SimpleNamespace(gerar_comissoes_venda=gerar),
    )

    resultado = vendas_comissoes._gerar_comissoes_pendentes_venda(
        None, venda, "tenant-a", "test"
    )

    assert ordem == ["lock", "ler", "commit", "lock", "ler"]
    assert [chamada["parcela_numero"] for chamada in chamadas] == [1]
    assert resultado == {"comissoes_geradas": 1, "total_comissoes": 5.0}


def test_atualizar_venda_deixa_comissoes_e_fechamento_para_finalizacao():
    source = inspect.getsource(vendas_routes.atualizar_venda)

    assert "_gerar_comissoes_pendentes_venda(" not in source
    assert 'venda.status = "finalizada"' not in source


def test_reprocessamento_nao_gera_comissao_do_lote_estornado_nem_da_contrapartida():
    pagamentos = [
        (10, "Pix", 50, None, 99, "confirmado"),
        (11, "Credito", 25, None, None, "confirmado"),
        (12, "Pix", -50, None, 99, "confirmado"),
        (13, "Pix", 50, None, 100, "confirmado"),
    ]

    liquidos = list(vendas_comissoes._pagamentos_liquidos_para_comissao(pagamentos))

    assert [
        (parcela, pagamento[0], valor) for parcela, pagamento, valor in liquidos
    ] == [
        (2, 11, Decimal("25")),
        (4, 13, Decimal("50")),
    ]


def test_compensacao_da_comissao_nao_usa_estorno_de_outro_lote_ou_forma():
    pagamentos = [
        (10, "Pix", 50, None, 99, "confirmado"),
        (11, "Credito", 20, None, 99, "confirmado"),
        (12, "Pix", -30, None, 99, "confirmado"),
        (13, "Pix", -50, None, 100, "confirmado"),
        (14, "Pix", 50, None, 101, "estornado"),
    ]

    liquidos = list(vendas_comissoes._pagamentos_liquidos_para_comissao(pagamentos))

    assert [
        (parcela, pagamento[0], valor) for parcela, pagamento, valor in liquidos
    ] == [
        (1, 10, Decimal("20")),
        (2, 11, Decimal("20")),
    ]
