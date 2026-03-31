import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.integracao_bling_nf_routes import (
    _registrar_nf_no_pedido,
    _localizar_pedido_local_por_numero_bling,
    _localizar_pedido_local_por_numero_loja,
    _nf_webhook_autorizada,
)
from app.services.bling_nf_service import processar_nf_autorizada, processar_nf_cancelada


def test_nf_autorizada_baixa_estoque_uma_vez(monkeypatch):
    db = Mock()
    db.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
        [],
        [SimpleNamespace(produto_id=12, documento="010001", observacao="Baixa automatica via NF 010001")],
    ]
    pedido = SimpleNamespace(
        status="aberto",
        confirmado_em=None,
        tenant_id="tenant-1",
        id=77,
        pedido_bling_numero="#11397",
        payload={"ultima_nf": {"numero": "010001"}},
    )
    item = SimpleNamespace(sku="026209.1", quantidade=1, vendido_em=None)
    produto = SimpleNamespace(id=12, tipo_kit=None, tipo_produto="SIMPLES")
    chamadas_baixa = []

    def fake_confirmar_venda(db_arg, item_arg):
        item_arg.vendido_em = "2026-03-24T00:00:00Z"

    def fake_buscar_produto(**kwargs):
        assert kwargs["sku"] == "026209.1"
        return produto

    def fake_baixar_item(**kwargs):
        chamadas_baixa.append(kwargs)
        return {"movimentos": [{"produto_id": 12, "quantidade": 1.0}]}

    monkeypatch.setattr(
        "app.services.bling_nf_service.buscar_produto_do_item",
        fake_buscar_produto,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.EstoqueReservaService.confirmar_venda",
        fake_confirmar_venda,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service._obter_usuario_padrao_tenant",
        lambda **kwargs: SimpleNamespace(id=99),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda **kwargs: [12],
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.baixar_estoque_item_integrado",
        fake_baixar_item,
    )
    monkeypatch.setattr("app.services.bling_nf_service.registrar_evento", lambda **kwargs: None)
    monkeypatch.setattr("app.services.bling_nf_service.abrir_incidente", lambda **kwargs: None)
    monkeypatch.setattr(
        "app.services.bling_nf_service.resolver_incidentes_relacionados",
        lambda *args, **kwargs: 0,
    )

    resposta_1 = processar_nf_autorizada(db=db, pedido=pedido, itens=[item], nf_id="98765")
    resposta_2 = processar_nf_autorizada(db=db, pedido=pedido, itens=[item], nf_id="98765")

    assert resposta_1 == "venda_confirmada"
    assert resposta_2 == "venda_ja_confirmada"
    assert pedido.status == "confirmado"
    assert item.vendido_em is not None
    assert len(chamadas_baixa) == 1
    assert chamadas_baixa[0]["produto"].id == 12
    assert chamadas_baixa[0]["documento"] == "010001"
    assert chamadas_baixa[0]["motivo"] == "venda_bling"
    assert chamadas_baixa[0]["user_id"] == 99


def test_nf_autorizada_reaproveita_baixa_legada_e_normaliza_para_nf(monkeypatch):
    db = Mock()
    movimento_legado = SimpleNamespace(
        id=3015,
        produto_id=12,
        documento="11733",
        observacao="Baixa automatica via webhook Bling (Atendido)",
        status="confirmado",
    )
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [movimento_legado]
    pedido = SimpleNamespace(
        status="confirmado",
        confirmado_em=None,
        tenant_id="tenant-1",
        id=77,
        pedido_bling_numero="11733",
        payload={"ultima_nf": {"numero": "011089"}},
    )
    item = SimpleNamespace(sku="026209.1", quantidade=1, vendido_em=None)
    produto = SimpleNamespace(id=12, tipo_kit=None, tipo_produto="SIMPLES")
    chamadas_baixa = []

    monkeypatch.setattr(
        "app.services.bling_nf_service.buscar_produto_do_item",
        lambda **kwargs: produto,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.EstoqueReservaService.confirmar_venda",
        lambda db_arg, item_arg: setattr(item_arg, "vendido_em", "2026-03-31T01:00:00Z"),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service._obter_usuario_padrao_tenant",
        lambda **kwargs: SimpleNamespace(id=99),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda **kwargs: [12],
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.baixar_estoque_item_integrado",
        lambda **kwargs: chamadas_baixa.append(kwargs) or {"movimentos": [{"produto_id": 12, "quantidade": 1.0}]},
    )
    monkeypatch.setattr("app.services.bling_nf_service.registrar_evento", lambda **kwargs: None)
    monkeypatch.setattr("app.services.bling_nf_service.abrir_incidente", lambda **kwargs: None)
    monkeypatch.setattr(
        "app.services.bling_nf_service.resolver_incidentes_relacionados",
        lambda *args, **kwargs: 0,
    )

    resposta = processar_nf_autorizada(db=db, pedido=pedido, itens=[item], nf_id="25441651448")

    assert resposta == "venda_confirmada"
    assert chamadas_baixa == []
    assert item.vendido_em is not None
    assert movimento_legado.documento == "011089"
    assert movimento_legado.observacao == "Baixa automatica via NF 011089"


def test_nf_autorizada_autocadastra_produto_e_baixa(monkeypatch):
    db = Mock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    pedido = SimpleNamespace(
        status="aberto",
        confirmado_em=None,
        tenant_id="tenant-1",
        id=88,
        pedido_bling_numero="#22001",
        payload={"ultima_nf": {"numero": "010002"}},
    )
    item = SimpleNamespace(sku="SKU-NOVO-001", quantidade=2, vendido_em=None)
    produto_autocriado = SimpleNamespace(id=345, tipo_kit=None, tipo_produto="SIMPLES")
    chamadas_baixa = []

    def fake_confirmar_venda(db_arg, item_arg):
        item_arg.vendido_em = "2026-03-24T00:00:00Z"

    def fake_buscar_produto(**kwargs):
        return None

    def fake_autocriar_produto(**kwargs):
        assert kwargs["sku"] == "SKU-NOVO-001"
        return produto_autocriado

    def fake_baixar_item(**kwargs):
        chamadas_baixa.append(kwargs)
        return {"movimentos": [{"produto_id": 345, "quantidade": 2.0}]}

    monkeypatch.setattr(
        "app.services.bling_nf_service.buscar_produto_do_item",
        fake_buscar_produto,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.criar_produto_automatico_do_bling",
        fake_autocriar_produto,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.EstoqueReservaService.confirmar_venda",
        fake_confirmar_venda,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service._obter_usuario_padrao_tenant",
        lambda **kwargs: SimpleNamespace(id=77),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda **kwargs: [345],
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.baixar_estoque_item_integrado",
        fake_baixar_item,
    )
    monkeypatch.setattr("app.services.bling_nf_service.registrar_evento", lambda **kwargs: None)
    monkeypatch.setattr("app.services.bling_nf_service.abrir_incidente", lambda **kwargs: None)
    monkeypatch.setattr(
        "app.services.bling_nf_service.resolver_incidentes_relacionados",
        lambda *args, **kwargs: 0,
    )

    resposta = processar_nf_autorizada(db=db, pedido=pedido, itens=[item], nf_id="99100")

    assert resposta == "venda_confirmada"
    assert len(chamadas_baixa) == 1
    assert chamadas_baixa[0]["produto"].id == 345
    assert chamadas_baixa[0]["quantidade"] == pytest.approx(2.0)


def test_nf_autorizada_baixa_componentes_do_produto_composto(monkeypatch):
    db = Mock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    pedido = SimpleNamespace(
        status="aberto",
        confirmado_em=None,
        tenant_id="tenant-1",
        id=1088,
        pedido_bling_numero="#11595",
        payload={"ultima_nf": {"numero": "010003"}},
    )
    item = SimpleNamespace(sku="022860.1/2", quantidade=1, vendido_em=None)
    produto_composto = SimpleNamespace(id=6814, tipo_kit="VIRTUAL", tipo_produto="VARIACAO")
    chamadas_baixa = []

    monkeypatch.setattr(
        "app.services.bling_nf_service.buscar_produto_do_item",
        lambda **kwargs: produto_composto,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service._obter_usuario_padrao_tenant",
        lambda **kwargs: SimpleNamespace(id=15),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda **kwargs: [6401],
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.EstoqueReservaService.confirmar_venda",
        lambda db_arg, item_arg: setattr(item_arg, "vendido_em", "2026-03-28T22:03:22Z"),
    )

    def fake_baixar_item(**kwargs):
        chamadas_baixa.append(kwargs)
        return {
            "movimentos": [
                {"produto_id": 6401, "quantidade": 2.0, "kit_origem_id": 6814},
            ]
        }

    monkeypatch.setattr(
        "app.services.bling_nf_service.baixar_estoque_item_integrado",
        fake_baixar_item,
    )
    monkeypatch.setattr("app.services.bling_nf_service.registrar_evento", lambda **kwargs: None)
    monkeypatch.setattr("app.services.bling_nf_service.abrir_incidente", lambda **kwargs: None)
    monkeypatch.setattr(
        "app.services.bling_nf_service.resolver_incidentes_relacionados",
        lambda *args, **kwargs: 0,
    )

    resposta = processar_nf_autorizada(db=db, pedido=pedido, itens=[item], nf_id="25428294101")

    assert resposta == "venda_confirmada"
    assert len(chamadas_baixa) == 1
    assert chamadas_baixa[0]["produto"].id == 6814
    assert chamadas_baixa[0]["user_id"] == 15


def test_localiza_pedido_por_numero_loja_em_payload_do_bling():
    db = Mock()
    pedido = SimpleNamespace(
        payload={
            "pedido": {"numeroLoja": "260329CXSEF6VM"},
            "webhook": {"numeroLoja": "260329CXSEF6VM"},
        }
    )
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        pedido
    ]

    encontrado = _localizar_pedido_local_por_numero_loja(
        db,
        tenant_id="tenant-1",
        numero_pedido_loja="260329CXSEF6VM",
    )

    assert encontrado is pedido


def test_localiza_pedido_por_numero_bling():
    db = Mock()
    pedido = SimpleNamespace(id=55, pedido_bling_numero="11598")
    db.query.return_value.filter.return_value.first.return_value = pedido

    encontrado = _localizar_pedido_local_por_numero_bling(
        db,
        tenant_id="tenant-1",
        pedido_bling_numero="11598",
    )

    assert encontrado is pedido


def test_registrar_nf_no_pedido_salva_data_emissao():
    pedido = SimpleNamespace(payload={})

    _registrar_nf_no_pedido(
        pedido=pedido,
        data={
            "numero": "011008",
            "serie": "2",
            "situacao": 5,
            "chaveAcesso": "CHAVE-TESTE",
            "valorTotalNf": 440.13,
            "dataEmissao": "2026-03-30",
        },
        nf_id="25432772133",
        situacao_num=5,
    )

    assert pedido.payload["ultima_nf"]["id"] == "25432772133"
    assert pedido.payload["ultima_nf"]["numero"] == "011008"
    assert pedido.payload["ultima_nf"]["data_emissao"] == "2026-03-30"


def test_registrar_nf_no_pedido_preserva_numero_existente_quando_webhook_vem_incompleto():
    pedido = SimpleNamespace(
        payload={
            "ultima_nf": {
                "id": "25432772133",
                "numero": "011008",
                "serie": "2",
                "situacao": "Pendente",
            }
        }
    )

    _registrar_nf_no_pedido(
        pedido=pedido,
        data={
            "situacao": 5,
            "valorTotalNf": 440.13,
        },
        nf_id="25432772133",
        situacao_num=5,
    )

    assert pedido.payload["ultima_nf"]["id"] == "25432772133"
    assert pedido.payload["ultima_nf"]["numero"] == "011008"
    assert pedido.payload["ultima_nf"]["serie"] == "2"
    assert pedido.payload["ultima_nf"]["situacao"] == "Autorizada"


def test_registrar_nf_no_pedido_nao_substitui_ultima_nf_por_nota_mais_antiga():
    pedido = SimpleNamespace(
        payload={
            "ultima_nf": {
                "id": "25441651448",
                "numero": "011089",
                "serie": "2",
                "situacao": "Autorizada",
                "data_emissao": "2026-03-30 19:28:21",
            }
        }
    )

    _registrar_nf_no_pedido(
        pedido=pedido,
        data={
            "numero": "011088",
            "serie": "2",
            "situacao": 5,
            "dataEmissao": "2026-03-30 19:28:16",
        },
        nf_id="25441651001",
        situacao_num=5,
    )

    assert pedido.payload["ultima_nf"]["id"] == "25441651448"
    assert pedido.payload["ultima_nf"]["numero"] == "011089"


def test_nf_webhook_considera_autorizada_quando_texto_da_nf_diz_autorizada_mesmo_com_codigo_6():
    assert _nf_webhook_autorizada(
        {
            "situacao": {"id": 6, "descricao": "Autorizada"},
            "numero": "011099",
        },
        situacao_num=6,
    ) is True


def test_nf_autorizada_nao_faz_fallback_para_numero_do_pedido_no_documento(monkeypatch):
    db = Mock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    pedido = SimpleNamespace(
        status="aberto",
        confirmado_em=None,
        tenant_id="tenant-1",
        id=89,
        pedido_bling_numero="#22002",
        payload={"ultima_nf": {"id": "25443132613"}},
    )
    item = SimpleNamespace(sku="SKU-SEM-NUMERO", quantidade=1, vendido_em=None)
    produto = SimpleNamespace(id=346, tipo_kit=None, tipo_produto="SIMPLES")
    chamadas_baixa = []

    monkeypatch.setattr(
        "app.services.bling_nf_service.buscar_produto_do_item",
        lambda **kwargs: produto,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.EstoqueReservaService.confirmar_venda",
        lambda db_arg, item_arg: setattr(item_arg, "vendido_em", "2026-03-31T01:00:00Z"),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service._obter_usuario_padrao_tenant",
        lambda **kwargs: SimpleNamespace(id=77),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda **kwargs: [346],
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.baixar_estoque_item_integrado",
        lambda **kwargs: chamadas_baixa.append(kwargs) or {"movimentos": [{"produto_id": 346, "quantidade": 1.0}]},
    )
    monkeypatch.setattr("app.services.bling_nf_service.registrar_evento", lambda **kwargs: None)
    monkeypatch.setattr("app.services.bling_nf_service.abrir_incidente", lambda **kwargs: None)
    monkeypatch.setattr(
        "app.services.bling_nf_service.resolver_incidentes_relacionados",
        lambda *args, **kwargs: 0,
    )

    resposta = processar_nf_autorizada(db=db, pedido=pedido, itens=[item], nf_id="25443132613")

    assert resposta == "venda_confirmada"
    assert len(chamadas_baixa) == 1
    assert chamadas_baixa[0]["documento"] is None


def test_nf_cancelada_estorna_baixa_e_reabre_lote(monkeypatch):
    class FakeQuery:
        def __init__(self, resultado):
            self.resultado = resultado

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self.resultado if isinstance(self.resultado, list) else []

        def first(self):
            return self.resultado

    class FakeDB:
        def __init__(self, movimentos, lote):
            self.movimentos = movimentos
            self.lote = lote
            self.commit_calls = 0

        def query(self, model):
            nome = getattr(model, "__name__", "")
            if nome == "EstoqueMovimentacao":
                return FakeQuery(self.movimentos)
            if nome == "ProdutoLote":
                return FakeQuery(self.lote)
            raise AssertionError(f"Modelo inesperado: {nome}")

        def add(self, obj):
            return None

        def commit(self):
            self.commit_calls += 1

    lote = SimpleNamespace(id=91, quantidade_disponivel=0.0, status="esgotado")
    movimentacao = SimpleNamespace(
        id=301,
        produto_id=6745,
        quantidade=1,
        lotes_consumidos=json.dumps([{"lote_id": 91, "quantidade": 1}]),
        status="confirmado",
        observacao="Baixa automatica via NF",
        user_id=12,
    )
    pedido = SimpleNamespace(
        id=1098,
        tenant_id="tenant-1",
        status="confirmado",
        cancelado_em=None,
        payload={"ultima_nf": {"numero": "010985"}},
        pedido_bling_numero="11605",
    )
    item = SimpleNamespace(vendido_em="2026-03-30T12:00:00Z", liberado_em=None)
    chamadas_estorno = []

    monkeypatch.setattr(
        "app.services.bling_nf_service._obter_usuario_padrao_tenant",
        lambda **kwargs: SimpleNamespace(id=55),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.KitEstoqueService.recalcular_kits_que_usam_produto",
        lambda db, produto_id: {},
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service._sincronizar_cache_estoque_virtual",
        lambda db, tenant_id, kit_id: None,
    )

    def fake_estornar(**kwargs):
        chamadas_estorno.append(kwargs)
        return {"sucesso": True}

    monkeypatch.setattr("app.estoque.service.EstoqueService.estornar_estoque", fake_estornar)

    db = FakeDB([movimentacao], lote)
    resposta = processar_nf_cancelada(db=db, pedido=pedido, itens=[item], nf_id="25432772133")

    assert resposta == "venda_cancelada_com_estorno"
    assert pedido.status == "cancelado"
    assert item.vendido_em is None
    assert item.liberado_em is not None
    assert movimentacao.status == "cancelado"
    assert lote.quantidade_disponivel == pytest.approx(1.0)
    assert lote.status == "ativo"
    assert len(chamadas_estorno) == 1
    assert chamadas_estorno[0]["produto_id"] == 6745
    assert db.commit_calls == 1
